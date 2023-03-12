# django_mail_sender
Service for sending email distribution using a templates and a subscribers lists

## <span style="color: red">There is "n+1" query problems. I know it and how fix it, will optimized.</span>   

Service uses celery and redis for async tasks. On main page there is instructions for using service in Russian language.
Developed on python2/Django 1.11 as required by task terms.

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

