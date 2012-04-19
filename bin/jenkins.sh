#!/bin/sh
# This script makes sure that Jenkins can properly run your tests against your
# codebase.
set -e

DB_HOST="localhost"
DB_USER="hudson"

cd $WORKSPACE
VENV=$WORKSPACE/venv

echo "Starting build on executor $EXECUTOR_NUMBER..."

# Make sure there's no old pyc files around.
find . -name '*.pyc' -exec rm {} \;


if [ ! -d "$VENV" ]; then
    echo "Making virtualenv..."
    virtualenv $VENV --no-site-packages
    pip install --upgrade pip
fi
source $VENV/bin/activate
pip install coverage
pip install -r requirements/compiled.txt
pip install -r requirements/dev.txt

git submodule sync
git submodule update --init --recursive

if [ ! -d "$WORKSPACE/vendor" ]; then
    echo "No /vendor... crap."
    exit 1
fi

cat > settings/local.py <<SETTINGS
import logging
from settings import *

ROOT_URLCONF = 'workspace.urls'

# For absoluate urls
DOMAIN = "localhost"
PROTOCOL = "http://"
PORT = 8001

SITE_URL = '%s%s:%d' % (PROTOCOL, DOMAIN, PORT)
# Database name has to be set because of sphinx
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': '${DB_HOST}',
        'NAME': '${JOB_NAME}',
        'USER': 'hudson',
        'PASSWORD': '',
        'OPTIONS': {'init_command': 'SET storage_engine=InnoDB'},
        'TEST_NAME': 'test_${JOB_NAME}',
        'TEST_CHARSET': 'utf8',
        'TEST_COLLATION': 'utf8_general_ci',
    }
}

# Disable BrowserID Cert Checking
BROWSERID_DISABLE_CERT_CHECK = True

#Serve Profile Photos from django
UPLOAD_URL = '/media/uploads'

# Statsd Defaults -- adjust as needed
STATSD_HOST = 'localhost'
STATSD_PORT = 8125
STATSD_PREFIX = 'mozillians'

## Email

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DEBUG = TEMPLATE_DEBUG = True

# ElasticSearch
ES_DISABLED = False
ES_HOSTS = ['127.0.0.1:9200']
ES_INDEXES = dict(default='mozillians_dev')
SETTINGS

echo "Creating database if we need it..."
echo "CREATE DATABASE IF NOT EXISTS ${JOB_NAME}"|mysql -u $DB_USER -h $DB_HOST

echo "Database name: ${JOB_NAME}"

echo "Starting tests..."
export FORCE_DB=1

if [ -z $COVERAGE ]; then
    python manage.py test --noinput --with-xunit --logging-clear-handlers
else
    coverage run manage.py test --noinput --with-xunit --logging-clear-handlers
    coverage xml --omit='*migrations*' $(find apps lib -name '*.py')
fi

echo "FIN"
