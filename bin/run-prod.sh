#!/bin/sh

python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py compress --engine jinja2 --extension=.html
python manage.py rebuild_index --noinput
gunicorn mozillians.wsgi:application -b 0.0.0.0:${PORT:-8000} --log-file -
