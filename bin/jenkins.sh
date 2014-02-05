#!/bin/sh
# This script makes sure that Jenkins can properly run your tests against your
# codebase.
set -e

echo "Starting build on executor $EXECUTOR_NUMBER..."

DB_HOST="localhost"
DB_USER="hudson"

if [ -n $WORKSPACE ] ; then WORKSPACE=. ; fi

cd $WORKSPACE
if [ ! -d "$WORKSPACE/vendor" ]; then
    echo "No /vendor... crap."
    exit 1
fi

VENV=$WORKSPACE/venv

if [ -n $JOB_NAME ] ; then JOB_NAME=mozillians ; fi


# Make sure there's no old pyc files around.
find . -name '*.pyc' -exec rm {} \;

git submodule sync
git submodule update --init --recursive

if [ ! -d "$VENV" ]; then
    echo "Making virtualenv..."
    virtualenv $VENV --no-site-packages
fi
. $VENV/bin/activate
# If setuptools is too old, recent pips fail badly later on, so make sure we're at least at 0.8
pip install -U 'setuptools>=0.8'
pip install -r requirements/dev.txt

cat > mozillians/settings/local.py <<SETTINGS
# flake8: noqa

ROOT_URLCONF = 'mozillians.urls'
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
ES_INDEXES = dict(default='test_${JOB_NAME}', public='test_${JOB_NAME}_public')
ES_TIMEOUT = 60

COMPRESS_ENABLED = False

SETTINGS

echo "Database name: ${JOB_NAME}"
echo "Dropping Test database"
echo "DROP DATABASE IF EXISTS test_${JOB_NAME};"|mysql -u $DB_USER -h $DB_HOST

echo "Creating database if we need it..."
echo "CREATE DATABASE IF NOT EXISTS ${JOB_NAME}"|mysql -u $DB_USER -h $DB_HOST

echo "Updating product details."

python manage.py update_product_details

echo "Check PEP-8"
flake8 mozillians

echo "Starting tests..."
export FORCE_DB=1

if [ -z $COVERAGE ]; then
    python manage.py test --noinput
else
    coverage run --omit='*migrations*' manage.py test --noinput
    coverage xml --omit='*migrations*' $(find mozillians -name '*.py')
fi

echo "FIN"
