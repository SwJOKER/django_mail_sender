# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import uuid

import pymorphy2
from ckeditor.fields import RichTextField
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone


class Subscriber(models.Model):
    address = models.EmailField(max_length=100, null=False, verbose_name='email')
    subscribers_list = models.ForeignKey('SubscribersList', null=False, verbose_name='список рассылки')

    def get_context(self):
        context = {}
        variables_data = self.variabledata_set.all()
        context.update({data.variable.tag_name: data.value for data in variables_data})
        context.update({'email': self.address})
        return context

    @classmethod
    def type_name(cls):
        return cls.__name__

    def __unicode__(self):
        return self.address


class Smtp(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    host = models.CharField(max_length=50, null=False, blank=False, verbose_name='Сервер')
    port = models.IntegerField(null=False, blank=False,validators=[MaxValueValidator(65536), MinValueValidator(1)],
                               verbose_name='Порт')
    password = models.CharField(null=False, blank=False, max_length=60, verbose_name='Пароль')
    username = models.CharField(null=False, blank=False, max_length=60, verbose_name='Логин')
    send_from = models.EmailField(max_length=60, verbose_name='Исходящий адрес')
    ssl = models.BooleanField(null=False, blank=False, verbose_name='SSL')
    tls = models.BooleanField(null=False, blank=False, verbose_name='TLS')


class VariableData(models.Model):
    value = models.CharField(max_length=50)
    variable = models.ForeignKey('Variable', on_delete=models.CASCADE, null=False, blank=False)
    subscriber = models.ForeignKey('Subscriber', on_delete=models.CASCADE, null=False, blank=False)

    class Meta:
        unique_together = ('variable', 'subscriber')
        verbose_name = 'значение переменной'
        verbose_name_plural = 'значения переменных'


class Variable(models.Model):
    tag_name = models.CharField(max_length=40, null=False, blank=False, verbose_name='имя тега')
    verbose_name = models.CharField(max_length=40, null=False, blank=False, verbose_name='название')
    subscribers_list = models.ForeignKey('SubscribersList', on_delete=models.CASCADE, verbose_name='список рассылки')


    @classmethod
    def type_name(cls):
        return cls.__name__

    class Meta:
        unique_together = (('tag_name', 'subscribers_list'), ('verbose_name', 'subscribers_list'))
        verbose_name = 'переменная'
        verbose_name_plural = 'переменные'



class SubscribersList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=150, null=False, verbose_name='название списка')

    class Meta:
        unique_together = ('user', 'name')
        verbose_name = 'список рассылки'
        verbose_name_plural = 'списки рассылки'

    def __unicode__(self):
        morph = pymorphy2.MorphAnalyzer(lang='ru')
        recipients_count = self.subscriber_set.all().count()
        # proper word form with numeral
        recipient_word = morph.parse('адресат')[0].make_agree_with_number(recipients_count).word
        return '%s (%s %s)' % (self.name, recipients_count, recipient_word)

    # array for autocomplete in mail editor
    def autocomplete_array(self):
        variables = self.variable_set.all()
        var_list = []
        var_list.append({'id': 0, 'tag': '{{ email }}', 'name': 'Email'})
        for index, var in enumerate(variables):
            var_list.append({'id': index + 1, 'tag': '{{ ' + var.tag_name + ' }}', 'name': var.verbose_name})
        return var_list

    # tagset for check compatibility template and subsribers list
    def get_tag_set(self):
        variables = self.variable_set.all()
        tag_list = []
        tag_list.append('email')
        for var in variables:
            tag_list.append(var.tag_name)
        return set(tag_list)


class Task(models.Model):

    READY = 'r'
    ACTIVE = 'a'
    FINISHED = 'f'
    ERROR = 'e'
    SENDING = 's'
    ERROR_TEMPLATE = 't'
    PROCEED = 'p'

    deny_delete_status_list = [FINISHED, ACTIVE, SENDING]
    can_start_status_list = [READY, ERROR]  # Ready, error(couldnt connect)
    can_stop_status_list = [ACTIVE, SENDING]  # active, sending

    TASK_STATUS = (
        ('r', 'Готово к отправке'),  # ready
        ('a', 'Запланировано'),  # active
        ('f', 'Отправка завершена'),  # finished
        ('e', 'Ошибка соединения'),  # error smtp
        ('s', 'Отправка'),  # sending
        ('t', 'Ошибка шаблона'),  # template error
        ('p', 'Подготовка задания')  # proceed
    )

    class Meta:
        unique_together = ('name', 'user')
        verbose_name = 'задание'
        verbose_name_plural = 'задания'

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=120, verbose_name='имя рассылки')
    template = models.ForeignKey('Template', verbose_name='шаблон')
    subscribers_list = models.ForeignKey('SubscribersList', verbose_name='список рассылки')
    start_time = models.DateTimeField(verbose_name='отложенная отправка', null=True, blank=True)
    status = models.CharField(max_length=1, choices=TASK_STATUS, default='r')
    scheduled = models.BooleanField(default=False)
    celery_id = models.CharField(max_length=36, null=True)

    def can_delete(self):
        return self.status not in self.deny_delete_status_list

    def can_stop(self):
        return self.status in self.can_stop_status_list

    def can_start(self):
        return self.status in self.can_start_status_list

    def get_subscribers(self):
        return self.subscribers_list.subscriber_set.all()

    def get_ready_letters(self):
        return self.letter_set.all()

    def get_sended_letters(self):
        return self.letter_set.filter(send_time__isnull=False)

    def get_readed_letters(self):
        return self.letter_set.filter(read_datetime__isnull=False)

    def __unicode__(self):
        return 'Name: {}\nSend time:{}\nStatus:{}'.format(self.name, self.start_time, self.status)


class Letter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, null=False, on_delete=models.CASCADE)
    recipient = models.ForeignKey(Subscriber, on_delete=models.CASCADE)
    delivery_status = models.BooleanField(default=False)
    send_time = models.DateTimeField(null=True)
    read_datetime = models.DateTimeField(null=True)
    subject = models.CharField(max_length=200)
    content = models.TextField()

    class Meta:
        unique_together = ['task', 'recipient']
        verbose_name = 'письмо'
        verbose_name_plural = 'письма'

    def read(self):
        self.read_datetime = timezone.now()
        self.save()


class Template(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, verbose_name='Название:')
    subject = models.CharField(max_length=200, verbose_name='Тема:')
    body = RichTextField(null=False, verbose_name='HTML:')

    class Meta:
        verbose_name = 'шаблон'
        verbose_name_plural = 'шаблоны'

    def __unicode__(self):
        return self.name

