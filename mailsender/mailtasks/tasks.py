# -*- coding: utf-8 -*-
from __future__ import absolute_import

import smtplib
import socket

from celery import shared_task
from celery.exceptions import InvalidTaskError
from django.conf import settings
from django.core.mail import send_mail, EmailMessage
from django.core.mail.backends.smtp import EmailBackend
from django.db.models import Prefetch
from django.template import Context, TemplateSyntaxError
from django.urls import reverse
from django.utils import timezone

from .custom_template import CustomTemplate
from .models import Task, Letter, Subscriber, VariableData


def get_task(task_id):
    prefetch_variables_data = Prefetch('variables_data', queryset=VariableData.objects.select_related('variable'))
    prefetch_subscribers = Prefetch('subscribers_list__subscribers', queryset=Subscriber.objects
                                    .prefetch_related(prefetch_variables_data))
    task = Task.objects.filter(id=task_id).select_related('template', 'subscribers_list', 'user') \
        .prefetch_related(prefetch_subscribers, 'user__smtp', 'letters').first()
    if not task:
        raise InvalidTaskError('Task not found')
    return task


@shared_task
def task_send_reset_password_email(content, recipient):
    subject = u"Password Reset Requested"
    send_mail(subject, content, settings.DEFAULT_FROM_EMAIL, [recipient],
              auth_user=settings.EMAIL_HOST_USER,
              auth_password=settings.EMAIL_HOST_PASSWORD,
              fail_silently=False)


@shared_task
def make_mail_task(task_id):
    task = get_task(task_id)
    task.status = task.PROCEED
    task.save()
    template = task.template
    try:
        subject_template = CustomTemplate(template.subject)
        content_template = CustomTemplate(template.body)
    except TemplateSyntaxError:
        task.status = task.ERROR_TEMPLATE  # set template error status
        task.save()
        return
    subscribers = task.subscribers_list.subscribers.all()
    letters_objs = []
    for subscriber in subscribers:
        context = Context(subscriber.get_context())
        context = Context(context)
        letter = Letter()
        letter.task = task
        letter.recipient = subscriber
        letter.subject = subject_template.render(context)
        letter.content = content_template.render(context)
        letters_objs.append(letter)
    Letter.objects.bulk_create(letters_objs)
    task.status = task.READY  # set ready to send status
    task.save()


@shared_task(bind=True, autoretry_for=(smtplib.SMTPException, socket.error), retry_backoff=True, max_retries=5)
def start_task(self, task_id):
    task = get_task(task_id)
    if task.status == task.FINISHED:
        return
    letters = task.letters.all()
    smtp = task.user.smtp
    if smtp and letters.count():
        try:
            with EmailBackend(host=smtp.host, use_ssl=smtp.ssl, password=smtp.password,
                              username=smtp.username, use_tls=smtp.tls, port=smtp.port) as connection:
                task.status = task.SENDING
                task.save()
                for letter in letters:
                    if not letter.send_time:
                        status_link = u'<img src="%s"/>' % \
                                      (settings.SITE_URL + reverse(u'mailtasks:delivery_link',
                                                                   kwargs={u'uuid': letter.id}))
                        content = letter.content + status_link
                        subject = letter.subject
                        recipient = letter.recipient
                        email = EmailMessage(subject, content, smtp.send_from, [recipient], connection=connection)
                        email.content_subtype = 'html'
                        res = email.send(fail_silently=False)
                        if res:
                            letter.send_time = timezone.now()
                            letter.save()
            task.status = task.FINISHED  # set status sended
            task.start_time = timezone.now()
            task.save()
        except (smtplib.SMTPException, socket.error) as e:
            if (self.request.retries >= self.max_retries):
                task.status = task.ERROR  # set error status cuz connection problems
                task.save()
                return
            raise e
