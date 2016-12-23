import django
import smtplib

from celery import Celery
from django.core.mail import send_mail as default_send_mail
from django.core.mail import EmailMessage
from django.core.cache import cache
import requests
import sendgrid
import os
from sendgrid.helpers.mail import *
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'emailer.settings')
app = Celery()
#app = Celery('tasks', backend='amqp', broker='amqp://')
app.config_from_envvar('DJANGO_SETTINGS_MODULE')
from django.core.mail import EmailMessage
from django.conf import settings

@app.task(serializer = 'json', bind = True)
def email_task(self, *args, **kwargs):
    try:
        import pdb;pdb.set_trace()
        sg = sendgrid.SendGridAPIClient(apikey=settings.SENDGRID_API_KEY)
        for receiver in kwargs['receiver']:
	        sender = Email(kwargs['sender'])
	        subject = kwargs['subject']
	        receiver = Email(receiver)
	        content = Content("text/html", kwargs['html_message'])
	        mail = Mail(sender, subject, receiver, content)
	        response = sg.client.mail.send.post(request_body=mail.get())
	        return response.status_code
    except Exception as exc:
        self.retry(exc = exc)