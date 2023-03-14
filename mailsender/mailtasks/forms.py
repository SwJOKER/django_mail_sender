# -*- coding: utf-8 -*-
import datetime
import re

from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.forms import ModelForm, TextInput, \
    inlineformset_factory, BooleanField, DateTimeField, ModelChoiceField, BaseInlineFormSet, CharField
from django.forms.widgets import DateInput, DateTimeInput, PasswordInput
from django.utils import timezone, six
from django.utils.text import get_text_list
from django.utils.translation import ugettext

from .custom_template import CustomTemplate, CustomTemplateError
from .models import Template, Subscriber, SubscribersList, Task, Variable, VariableData, \
    Smtp


# try to create template and raise error if cant
def template_field_validator(value):
    try:
        CustomTemplate(value)
    except CustomTemplateError as e:
        raise ValidationError(str(e))


class TemplateForm(ModelForm):
    subscribers_list = ModelChoiceField(
        queryset=SubscribersList.objects.none(),
        required=False,
        label='',
        empty_label=u'Загрузить переменные из списка рассылки'
    )

    class Meta:
        model = Template
        fields = ['name', 'subject', 'subscribers_list', 'body']
        widgets = {
            'name': TextInput(attrs={'placeholder': u'Название шаблона'}),
            'subject': TextInput(attrs={'placeholder': u'Можно использовать переменные шаблона в виде {{ var }}'})
        }

    # additional field 'subscribers_sist' for load autocomplete when chose
    def __init__(self, *args, **kwargs):
        super(TemplateForm, self).__init__(*args, **kwargs)
        self.fields['subscribers_list'].queryset = SubscribersList.objects.filter(user=self.instance.user)
        self.fields['subject'].validators.append(template_field_validator)
        self.fields['body'].validators.append(template_field_validator)


class SubscriberForm(ModelForm):
    class Meta:
        model = Subscriber
        fields = ['address']


class CustomFormSet(BaseInlineFormSet):
    # collect form errors and delete duplicates
    def input_distinct_errors(self):
        res = []
        for errs in self.errors:
            for key, val in errs.items():
                if val not in res and key != '__all__':
                    res.append(val)
        return res + self.non_form_errors()

    # a verbose name of field in error instead a common name
    def get_unique_error_message(self, unique_check):
        unique_check = [field for field in unique_check if field != self.fk.name]
        if len(unique_check) == 1:
            return ugettext("Please correct the duplicate data for %(field)s.") % {
                "field": self.empty_form.fields[unique_check[0]].label,
            }
        else:
            unique_check_labels = [self.empty_form.fields[field].label for field in unique_check]
            return ugettext("Please correct the duplicate data for %(field)s, which must be unique.") % {
                "field": get_text_list(unique_check_labels, six.text_type(ugettext("and"))),
            }


class SubscribersCustomFormset(CustomFormSet):

    def __init__(self, *args, **kwargs):
        super(SubscribersCustomFormset, self).__init__(*args, **kwargs)
        self.queryset = kwargs.get('queryset')
        self._extra_variables = self.instance.variables.all()
        self.init_subscribers_vars()

    def get_queryset(self):
        if not self.queryset:
            prefetch_variables_data = Prefetch('variables_data',
                                               queryset=VariableData.objects.select_related('variable'))
            self.queryset = Subscriber.objects.filter(subscribers_list=self.instance).prefetch_related(
                prefetch_variables_data)
        return self.queryset

    def init_subscribers_vars(self):
        data = {}
        for subscriber in self.get_queryset():
            var_data = {x.variable.id: x for x in subscriber.variables_data.all() if x is not None}
            data.update({subscriber.id: var_data})
        self._subscribers_vars = data

    def get_variable_value(self, subscriber_id, var_id):
        var_data = self._subscribers_vars.get(subscriber_id)
        if var_data:
            return var_data.get(var_id).value

    def add_fields(self, form, index):
        super(SubscribersCustomFormset, self).add_fields(form, index)
        # var_data = {x.variable_id:x for x in form.instance.variables_data.all() if not x is None}
        for var in self._extra_variables:
            var_value = self.get_variable_value(form.instance.id, var.id)
            form.fields[var.tag_name] = CharField(max_length=50, label=var.verbose_name, required=True,
                                                  initial=var_value)
        form.fields[u'DELETE'] = form.fields.pop(u'DELETE')

    def save_variables_values(self, instance, form):
        for var_type in self._extra_variables:
            instance.variables_data.update_or_create(variable=var_type,
                                                     defaults={'value': form.cleaned_data[var_type.tag_name]})

    def save_new(self, form, commit=True):
        instance = form.save(commit=commit)
        if commit:
            self.save_variables_values(instance, form)
        return instance

    def save_existing(self, form, instance, commit=True):
        if commit:
            self.save_variables_values(instance, form)
        return form.save(commit=commit)


subscriber_formset_widgets = {'birth_date': DateInput(format='%Y-%m-%d',
                                                      attrs={'class': 'form-control', 'type': 'date',
                                                             'max': timezone.localdate() - datetime.timedelta(
                                                                 days=365 * 14),
                                                             })}

SubscribersFormSet = inlineformset_factory(SubscribersList, Subscriber,
                                           form=SubscriberForm,
                                           formset=SubscribersCustomFormset,
                                           can_delete=True,
                                           widgets=subscriber_formset_widgets)


class SmtpForm(ModelForm):
    class Meta:
        model = Smtp
        fields = '__all__'
        exclude = ('user', 'successful_connect')
        widgets = {
            'password': PasswordInput(),
        }


class SubscribersListForm(ModelForm):
    class Meta:
        model = SubscribersList
        fields = ['name']
        widgets = {
            'name': TextInput(attrs={'placeholder': u'Название списка'})
        }

    def full_clean(self):
        super(SubscribersListForm, self).full_clean()
        try:
            self.instance.validate_unique()
        except ValidationError:
            self.add_error('name', u'Название должно быть уникальным')


class TaskForm(ModelForm):
    class Meta:
        model = Task
        fields = '__all__'
        exclude = ('user', 'start_time', 'celery_id', 'status', 'scheduled')

    def full_clean(self):
        super(TaskForm, self).full_clean()
        try:
            self.instance.validate_unique()
        except ValidationError:
            self.add_error('name', u'Название должно быть уникальным')

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        for key, field in self.fields.items():
            if hasattr(field, 'queryset'):
                model = field.queryset.model
                field.queryset = model.objects.filter(user=self.instance.user)


class CommitTaskForm(ModelForm):
    class Meta:
        model = Task
        fields = ('scheduled', 'start_time',)

    scheduled = BooleanField(initial=False, label=u'Отложенная отправка', required=False)
    start_time = DateTimeField(required=False, input_formats=('%Y-%m-%dT%H:%M',),
                               widget=DateTimeInput(format='%Y-%m-%dT%H:%M',
                                                    attrs={'type': 'datetime-local',
                                                           'value': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                                                           'min': timezone.now().strftime('%Y-%m-%dT%H:%M'),
                                                           'required': False}))


class TagNameField(CharField):
    def to_python(self, value):
        return value.lower()


def tag_name_validator(value):
    regexp = r'[^a-z_0-9]'
    if re.search(pattern=regexp, string=value):
        raise ValidationError(u"Имя тега может содержать только английские буквы, без пробелов.")
    if value == 'email':
        raise ValidationError(u'Поле "email" включено по умолчанию. Выберите другое имя тега')


class VariableForm(ModelForm):
    tag_name = TagNameField(label=u'Имя тега', max_length=40, validators=[tag_name_validator])
    field_order = ['verbose_name', 'tag_name']

    class Meta:
        model = Variable
        fields = '__all__'


VariableFormSet = inlineformset_factory(SubscribersList, Variable, form=VariableForm, formset=CustomFormSet,
                                        can_delete=True)
