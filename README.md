# django_mail_sender
Service for sending email distribution using a templates and a subscribers lists

Service uses celery and redis for async tasks. On main page there is instructions for using service in Russian language.
Developed on python2/Django 1.11 as required by task terms.

### There are "n+1" query problems and bad practices. I know it and how fix it, will optimized. In process

## Quick Start

Start docker-compose container from project directory where yml file located. 
```
docker-compose up -d --build
```
On each restart DB clears and filled up data from json for testing.<br>

Test user:
```
Login: test123
Password: 12345
```

