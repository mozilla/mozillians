#!/bin/sh

python manage.py migrate --noinput
gunicorn mozillians.wsgi:application -b 0.0.0.0:${PORT:-8000} --log-file -
