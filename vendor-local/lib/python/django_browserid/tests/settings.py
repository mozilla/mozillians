# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
TEST_RUNNER = 'django_nose.runner.NoseTestSuiteRunner'

SECRET_KEY = 'asdf'

DATABASES = {
    'default': {
        'NAME': 'test.db',
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = (
    'django_nose',
    'django_browserid',
    'django_browserid.tests',

    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
)

ROOT_URLCONF = 'django_browserid.tests.urls'

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'django_browserid.auth.BrowserIDBackend',
)

BROWSERID_CREATE_USER = True
BROWSERID_USERNAME_ALGO = None

STATIC_URL = 'static/'
