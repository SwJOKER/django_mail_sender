#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

#python manage.py flush --no-input
python manage.py sqlflush | python manage.py dbshell
#python manage.py makemigrations
#python manage.py migrate
# fills up db test data
python manage.py loaddata test_db.json
python manage.py loaddata test_users_db.json


python manage.py collectstatic --noinput

exec "$@"