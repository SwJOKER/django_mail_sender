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
python manage.py makemigrations
python manage.py migrate
# fills up db test data
python manage.py loaddata test_users_db.json
python manage.py loaddata test_db.json
#cat ./test_db.json | python manage.py dbshell
#psql -h localhost -d databasename -U username -f "c://path_to_file.sql"
#
#if [ "$DJANGO_SUPERUSER_USERNAME" ]
#then
#    python manage.py createsuperuser \
#        --noinput \
#        --username $DJANGO_SUPERUSER_USERNAME \
#        --email $DJANGO_SUPERUSER_EMAIL
#fi

exec "$@"