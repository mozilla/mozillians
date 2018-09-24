#!/bin/sh

python manage.py migrate --noinput
gunicorn mozillians.wsgi:application -w 2 -b 0.0.0.0:8000 --log-file -
