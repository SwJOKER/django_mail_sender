# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import unicode_literals

import json
import os

from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.http import JsonResponse, HttpResponseRedirect, HttpResponse
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views import View
from django.views.generic import CreateView, ListView
from django.views.generic.detail import SingleObjectTemplateResponseMixin, DetailView
from django.views.generic.edit import UpdateView, DeleteView, BaseUpdateView

from .celery import app
from .custom_template import CustomTemplate, CustomTemplateError
from .forms import TemplateForm, SubscribersFormSet, SubscribersListForm, TaskForm, CommitTaskForm, VariableFormSet, \
    SmtpForm
from .models import Task, Template, SubscribersList, Letter, Variable, \
    Smtp
from .tasks import task_send_reset_password_email, make_mail_task, start_task


def view_404(request, exception=None):
    return redirect('/')


class CheckUserBelongingMixin(UserPassesTestMixin):
    def test_func(self):
        if self.request.user.is_authenticated:
            pk = self.kwargs['pk']
            obj = self.model.objects.get(pk=pk)
            login_user = self.request.user
            return login_user.pk == obj.user.pk
        else:
            return False


class IndexView(ListView):
    model = Task
    context_object_name = 'tasks'
    template_name = 'mailtasks/index.html'


class TemplatesView(LoginRequiredMixin, ListView):
    model = Template
    context_object_name = 'templates'
    template_name = 'mailtasks/templates.html'

    def get_queryset(self):
        return Template.objects.filter(user=self.request.user)


class TaskDetailView(LoginRequiredMixin, CheckUserBelongingMixin, UpdateView):
    form_class = CommitTaskForm
    model = Task
    template_name = 'mailtasks/task_detail.html'

    def get_context_data(self, **kwargs):
        context = super(TaskDetailView, self).get_context_data(**kwargs)
        if self.object.status == Task.FINISHED:
            del context['form']
        context['action_link'] = reverse_lazy('mailtasks:task_detail', kwargs={'pk': self.object.id})
        return context

    def get_success_url(self):
        return reverse_lazy('mailtasks:task_detail', kwargs={'pk': self.object.id})

    def form_valid(self, form):
        self.object = form.save()
        if self.object.can_start():
            if self.object.scheduled:
                self.object.status = Task.ACTIVE
                celery_task = start_task.apply_async((self.object.id,), eta=self.object.start_time)
                self.object.celery_id = celery_task.id
            else:
                # change status here, not in celery, cuz we need it for proper representation
                self.object.status = Task.SENDING  # send status
                start_task.delay(self.object.id)
            self.object.save()
            return HttpResponseRedirect(self.get_success_url())


class TaskStopView(TaskDetailView):
    def get(self, *args, **kwargs):
        return HttpResponseRedirect(self.get_success_url())

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        task_id = self.object.celery_id
        if task_id:
            app.control.revoke(task_id, terminate=True)
            self.object.celery_id = None
        self.object.status = Task.READY
        self.object.start_time = None;
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())


class TaskDeleteView(LoginRequiredMixin, CheckUserBelongingMixin, DeleteView):
    model = Task
    success_url = reverse_lazy('mailtasks:task_list')

    def get(self, request, *args, **kwargs):
        reverse_lazy('mailtasks:task_detail', kwargs={'pk': self.object.id})

    def post(self, request, *args, **kwargs):
        if self.get_object().can_delete():
            return self.delete(request, *args, **kwargs)
        else:
            return HttpResponseRedirect(reverse_lazy('mailtasks:task_detail', kwargs={'pk': self.object.id}))


class TemplateDeleteView(LoginRequiredMixin, CheckUserBelongingMixin, DeleteView):
    model = Template
    success_url = reverse_lazy('mailtasks:templates')

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse_lazy('mailtasks:template_detail', kwargs={'pk': self.object.id}))


class SubscribersListDeleteView(LoginRequiredMixin, CheckUserBelongingMixin, DeleteView):
    model = SubscribersList
    success_url = reverse_lazy('mailtasks:subscribers')

    def get(self, request, *args, **kwargs):
        reverse_lazy('mailtasks:subscribers_list_detail', kwargs={'pk': self.object.id})


class TemplateDetailView(LoginRequiredMixin, CheckUserBelongingMixin, UpdateView):
    form_class = TemplateForm
    model = Template
    template_name = 'mailtasks/new_template.html'
    success_url = reverse_lazy('mailtasks:templates')

    def get_context_data(self, **kwargs):
        context = super(TemplateDetailView, self).get_context_data(**kwargs)
        context['action_link'] = self.request.path_info
        context['subscribers_variables_url'] = '/mailtasks/subscribers/variables/'
        context['title'] = 'Шаблон'
        return context


class SubscribersListsView(LoginRequiredMixin, ListView):
    model = SubscribersList
    context_object_name = 'lists'
    template_name = 'mailtasks/subscribers_lists.html'

    def get_queryset(self):
        return SubscribersList.objects.filter(user=self.request.user)


class SubscribersListDetailView(LoginRequiredMixin, CheckUserBelongingMixin, UpdateView):
    form_class = SubscribersListForm
    model = SubscribersList
    template_name = 'mailtasks/subscribers_page.html'
    success_url = reverse_lazy('mailtasks:subscribers')
    formset_class = SubscribersFormSet
    title = 'Редактирование списка'

    def get_formset(self, *args, **kwargs):
        child_model = self.formset_class.fk.model
        if not child_model.objects.filter(**{self.formset_class.fk.name: self.object}).count():
            self.formset_class.extra = 1
        else:
            self.formset_class.extra = 0
        return self.formset_class(*args, **kwargs)

    def get_context_data(self, formset=None, **kwargs):
        context = super(SubscribersListDetailView, self).get_context_data(**kwargs)
        context['title'] = self.title
        context['action_link'] = self.request.path_info
        context['formset'] = formset or self.get_formset(instance=self.object)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        formset = self.get_formset(self.request.POST, instance=self.object)
        if form.is_valid() and formset.is_valid():
            return self.form_valid(form, formset)
        else:
            return self.form_invalid(form, formset)

    def form_valid(self, form, formset):
        self.object = form.save()
        formset.instance = self.object
        formset.save()
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form, formset):
        return self.render_to_response(self.get_context_data(form=form, formset=formset))


class EditSubsListVarsView(SubscribersListDetailView):
    template_name = 'mailtasks/subscribers_page.html'
    formset_class = VariableFormSet
    title = 'Редактирование переменных'

    def get_success_url(self):
        return reverse_lazy('mailtasks:subscribers_list_detail', kwargs={'pk': self.object.id})


class LetterDetailView(DetailView):
    model = Letter
    template_name = 'mailtasks/letter.html'


class SubscribersListCreateView(LoginRequiredMixin, CreateView):
    template_name = 'mailtasks/subscribers_page.html'
    form_class = SubscribersListForm
    model = SubscribersList
    title = 'Новый список'
    help_str = 'Настройте переменные для списка переменных, которые вы хотите использовать в шаблонах. ' \
               'Email включен по умолчанию. Если дополнительные переменные не требуются,' \
               'оставьте поля пустыми.'

    def get_form_kwargs(self):
        kwargs = super(SubscribersListCreateView, self).get_form_kwargs()
        kwargs.update({'instance': self.model(user=self.request.user)})
        return kwargs

    def get_context_data(self, formset=None, *args, **kwargs):
        context = super(SubscribersListCreateView, self).get_context_data(**kwargs)
        context['title'] = self.title
        context['action_link'] = self.request.path_info
        context['help'] = self.help_str
        if formset:
            context['formset'] = formset
        else:
            VariableFormSet.extra = 1
            context['formset'] = VariableFormSet(queryset=Variable.objects.none())
        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        formset = VariableFormSet(request.POST)
        if form.is_valid() and formset.is_valid():
            return self.form_valid(form, formset)
        else:
            return self.form_invalid(form, formset)

    def form_valid(self, form, formset):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.save()
        subscribers = formset.save(commit=False)
        for instance in subscribers:
            instance.subscribers_list = self.object
            instance.save()
        return redirect(reverse_lazy("mailtasks:subscribers_list_detail", kwargs={'pk': self.object.pk}))

    def form_invalid(self, form, formset):
        return self.render_to_response(
            self.get_context_data(form=form, formset=formset)
        )


# View for getting variable list for autocomplete in templates editor
class SubscribersVarsJsonView(LoginRequiredMixin, View):

    def post(self, request):
        if request.method == 'POST':
            request_data = json.loads(request.body)
            subs_list_pk = request_data['pk']
            try:
                instance = SubscribersList.objects.get(user=request.user, pk=subs_list_pk)
                variable_list = instance.autocomplete_array()
                return JsonResponse(variable_list, status=200, safe=False)
            except SubscribersList.DoesNotExist:
                return JsonResponse({}, status=403)


class CheckTemplateView(LoginRequiredMixin, View):
    template_overvars_message = 'Шаблон содержит переменные, которых нет в списке рассылки. ' \
                        'Переменные, которых нет в списке рассылки, будут удалены из текста письма.'

    def post(self, request):
        if request.method == 'POST':
            request_data = json.loads(request.body)
            template_pk = request_data['template_pk']
            subscribers_list_pk = request_data['subscribers_list_pk']
            try:
                subs_list = SubscribersList.objects.get(user=request.user, pk=subscribers_list_pk)
                template = Template.objects.get(user=request.user, pk=template_pk)
            except (SubscribersList.DoesNotExist, Template.DoesNotExist):
                return JsonResponse({}, status=403)
            try:
                template_tags = CustomTemplate(template.subject).get_template_tags() + \
                                CustomTemplate(template.body).get_template_tags()
            except CustomTemplateError as e:
                message = str(e)
                return JsonResponse({'result': False, 'message': message}, status=406, safe=False)
            if template_tags:
                message = self.template_overvars_message
                result = set(template_tags).issubset(subs_list.get_tag_set())
            else:
                result = True
            return JsonResponse({'result': result, 'message': message}, status=200, safe=False)


class CreateTemplateView(LoginRequiredMixin, CreateView):
    form_class = TemplateForm
    template_name = 'mailtasks/new_template.html'
    success_url = reverse_lazy('mailtasks:templates')
    model = Template

    def get_form_kwargs(self):
        kwargs = super(CreateTemplateView, self).get_form_kwargs()
        kwargs.update({'instance': self.model(user=self.request.user)})
        return kwargs

    def form_valid(self, form):
        self.get_form_kwargs()
        form.instance.user = self.request.user
        return super(CreateTemplateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = CreateView.get_context_data(self, **kwargs)
        context['action_link'] = reverse_lazy('mailtasks:new_template')
        context['title'] = 'Новый шаблон'
        context['subscribers_variables_url'] = '/mailtasks/subscribers/variables/'
        return context


def post_login(request):
    if request.method == "POST":
        request_data = json.loads(request.body)
        username = request_data['username']
        password = request_data['password']
        user = authenticate(username=username, password=password)
        print User.objects.all()
        if user is not None:
            login(request, user)
            return JsonResponse({'user': username})
        else:
            return JsonResponse({'error': 'Неверный логин или пароль'})


class PasswordReset(View):

    def post(self, request, *args, **kwargs):
        if request.method == "POST":
            password_reset_form = PasswordResetForm(json.loads(request.body))
            if password_reset_form.is_valid():
                data = password_reset_form.cleaned_data['email']
                associated_users = User.objects.filter(email=data)
                if associated_users:
                    for user in associated_users:
                        c = {
                            "email": user.email,
                            'domain': settings.DOMAIN,
                            'site_name': 'MailTasker',
                            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                            "user": user,
                            'token': default_token_generator.make_token(user),
                            'protocol': 'http',
                        }
                        email_template_name = "registration/reset_pwd_mail.html"
                        email = render_to_string(email_template_name, c)
                        task_send_reset_password_email.delay(email, user.email)
                        return JsonResponse({'msg': 'На вашу почту отправлена инструкция по восстановлению пароля'})
                else:
                    return JsonResponse({'error': 'Такого пользователя нет в базе'}, )
            else:
                return JsonResponse({'error': 'Неправильный адрес почты'})


class TrackMessageView(View):
    def get(self, *args, **kwargs):
        with open(os.path.join(settings.STATIC_ROOT, 'mailtasks/1px.jpg'), 'rb') as image:
            try:
                letter = Letter.objects.get(pk=self.kwargs['uuid'])
            except Letter.DoesNotExist:
                return HttpResponse(status=404)
            letter.read()
            return HttpResponse(image.read(), content_type="image/jpeg", status=201)


class RegisterView(View):

    def email_validate(self):
        email = json.loads(self.request.body)['email'].lower()
        user = User.objects.filter(email=email)
        if user.count():
            return False
        return True

    def password_validate(self):
        password1 = json.loads(self.request.body)['password1']
        password2 = json.loads(self.request.body)['password2']
        return password1 and password2 and password1 == password2

    def username_validate(self):
        username = json.loads(self.request.body)['username']
        user = User.objects.filter(username=username)
        if user.count():
            return False
        return True

    def post(self, request):
        self.request = request
        if request.method == "POST":
            response = {}
            request_data = json.loads(request.body)
            if self.username_validate():
                username = request_data['username']
            else:
                response['error'] = 'username'
                response['error_msg'] = 'Логин уже занят'
                return JsonResponse(response)
            if self.email_validate():
                email = request_data['email'].lower()
            else:
                response['error'] = 'email'
                response['error_msg'] = 'Email уже занят'
                return JsonResponse(response)
            if self.password_validate():
                password = request_data['password1']
            else:
                response['error'] = 'password'
                response['error_msg'] = 'Пароли не совпадают'
                return JsonResponse(response)
            user = User.objects.create_user(username=username, password=password, email=email)
            user.save()
            response = {'status': 'ok'}
            return JsonResponse(response)


class CreateTaskView(LoginRequiredMixin, CreateView):
    form_class = TaskForm
    template_name = 'mailtasks/new_task.html'
    model = Task

    def get_form_kwargs(self):
        kwargs = super(CreateTaskView, self).get_form_kwargs()
        kwargs.update({'instance': self.model(user=self.request.user)})
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(CreateTaskView, self).get_context_data(**kwargs)
        context['action_link'] = self.request.path_info
        return context

    def form_valid(self, form):
        form.instance.user = self.request.user
        self.object = form.save()
        make_mail_task.delay(self.object.id)
        return super(CreateTaskView, self).form_valid(form)

    def get_success_url(self):
        return reverse_lazy('mailtasks:task_detail', kwargs={'pk': self.object.id})


class CreateSmtpView(LoginRequiredMixin, SingleObjectTemplateResponseMixin, BaseUpdateView):
    model = Smtp
    template_name = 'mailtasks/smtp_settings.html'
    success_url = reverse_lazy('mailtasks:templates')
    form_class = SmtpForm

    def get_object(self):
        user = self.request.user
        try:
            return user.smtp
        except Smtp.DoesNotExist as e:
            return Smtp(user=user)

    def form_valid(self, form):
        self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())


class TaskListView(LoginRequiredMixin, ListView):
    model = SubscribersList
    context_object_name = 'tasks'
    template_name = 'mailtasks/task_list.html'

    def get_queryset(self):
        return Task.objects.filter(user=self.request.user)


