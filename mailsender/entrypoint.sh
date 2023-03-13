#!/bin/sh

if [ "$DATABASE" = "postgres" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $SQL_HOST $SQL_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

# erase db
python manage.py flush --no-input
rm -rf ./mailtasks/migrations
# init migrations
python manage.py makemigrations mailtasks
python manage.py migrate
### fills up db test data
python manage.py loaddata test_users_db.json
python manage.py loaddata test_db.json

exec "$@"