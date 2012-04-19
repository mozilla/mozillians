# -*- coding: utf-8 -*-

# Django settings for the mozillians project.
import logging

from funfactory.manage import path
from funfactory import settings_base as base
from settings import initial as pre

## Log settings
SYSLOG_TAG = "http_app_mozillians"
LOGGING = {
    'loggers': {
        'landing': {'level': logging.INFO},
        'phonebook': {'level': logging.INFO},
    },
}

## L10n
LOCALE_PATHS = [path('locale')]

# Accepted locales
PROD_LANGUAGES = ('ca', 'cs', 'de', 'en-US', 'es', 'hu', 'fr', 'ko', 'nl',
                  'pl', 'pt-BR', 'ru', 'sk', 'sl', 'sq', 'zh-TW')

# List of RTL locales known to this project. Subset of LANGUAGES.
RTL_LANGUAGES = ()  # ('ar', 'fa', 'fa-IR', 'he')

# For absoluate urls
PROTOCOL = "https://"
PORT = 443

## Media and templates.
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    path('staticfiles'),
)

STATIC_ROOT = path('media')


MEDIA_URL = '/uploads/'

# Deprecated with django 1.4
ADMIN_MEDIA_PREFIX = None

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'jingo.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = list(base.TEMPLATE_CONTEXT_PROCESSORS) + [
    'django_browserid.context_processors.browserid_form',
    'django.core.context_processors.static',
]

JINGO_EXCLUDE_APPS = [
    'bootstrapform',
    'admin',
]

DEFAULT_IMAGE_SRC = 'img/unknown.png'

MINIFY_BUNDLES = {
    'css': {
        'common': (
            'css/bootstrap.css',
            'css/jquery-ui-1.8.16.custom.css',
            'js/libs/tag-it/css/jquery.tagit.css',
            'css/base.css',
            'css/bootstrap-responsive.css',
            'css/base-480px.css',
            'css/base-768px.css',
            'css/base-980px.css',
        ),
        'test': (
            'css/qunit.css',
        ),
    },
    'js': {
        'common': (
            'js/libs/jquery-1.7.2.js',
            'js/libs/jquery-ui-1.8.7.custom.min.js',
            'js/libs/bootstrap/bootstrap-transition.js',
            'js/libs/bootstrap/bootstrap-alert.js',
            'js/libs/bootstrap/bootstrap-modal.js',
            'js/libs/bootstrap/bootstrap-dropdown.js',
            'js/libs/bootstrap/bootstrap-tooltip.js',
            'js/libs/bootstrap/bootstrap-popover.js',
            'js/libs/bootstrap/bootstrap-button.js',
            'js/libs/bootstrap/bootstrap-collapse.js',
            'js/libs/bootstrap/bootstrap-carousel.js',
            'js/libs/bootstrap/bootstrap-typeahead.js',
            'js/libs/bootstrap/bootstrap-tab.js',
            'js/libs/validation/validation.js',
            'js/main.js',
            'js/browserid.js',
            'js/groups.js',
        ),
        'edit_profile': (
            'js/libs/tag-it/js/tag-it.js',
        ),
        'search': (
            'js/libs/jquery.endless-scroll.js',
            'js/infinite.js',
            'js/expand.js',
        ),
        'backbone': (
            'js/libs/underscore.js',
            'js/libs/backbone.js',
            'js/libs/backbone.localStorage.js',
            'js/profiles.js',
        ),
        'test': (
            'js/libs/qunit.js',
            'js/tests/test.js',
        ),
    }
}

MIDDLEWARE_CLASSES = list(base.MIDDLEWARE_CLASSES) + [
    'commonware.response.middleware.StrictTransportMiddleware',
    'commonware.response.middleware.GraphiteMiddleware',
    'commonware.response.middleware.GraphiteRequestTimingMiddleware',
    'csp.middleware.CSPMiddleware',
    'phonebook.middleware.PermissionDeniedMiddleware',
]

# StrictTransport
STS_SUBDOMAINS = True

# Not all URLs need locale.
SUPPORTED_NONLOCALES = list(base.SUPPORTED_NONLOCALES) + [
    'csp',
]

AUTHENTICATION_BACKENDS = ('common.backends.MozilliansBrowserID',)

# BrowserID creates a user if one doesn't exist.
BROWSERID_CREATE_USER = True

# On Login, we redirect through register.
LOGIN_REDIRECT_URL = '/register'

INSTALLED_APPS = (
    # Local apps
    'funfactory',  # Content common to most playdoh-based apps.
    'jingo_minify',
    'tower',  # for ./manage.py extract (L10n)
    'cronjobs',  # for ./manage.py cron * cmd line tasks

    # Django contrib apps
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.admin',

    # Our apps. These need to go in order of migration.
    'users',
    'phonebook',
    'groups',
    'taskboard',
    'common',
    # 'locations',

    # Third party apps
    'bootstrapform',
    'csp',
    'commonware.response.cookies',
    'django_browserid',
    'djcelery',
    'elasticutils',
    'sorl.thumbnail',
    'south',
    'django_nose',  # Load last to enforce dominance.
)

HMAC_KEYS = {
    '2011-01-01': 'cheesecake',
    '2012-01-01': 'foobar',
}

BASE_PASSWORD_HASHERS = (
    'django_sha2.hashers.BcryptHMACCombinedPasswordVerifier',
    'django_sha2.hashers.SHA512PasswordHasher',
    'django_sha2.hashers.SHA256PasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.UnsaltedMD5PasswordHasher',
)

from django_sha2 import get_password_hashers
PASSWORD_HASHERS = get_password_hashers(BASE_PASSWORD_HASHERS, HMAC_KEYS)


SESSION_COOKIE_HTTPONLY = True
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"

# Email
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Auth
LOGIN_URL = '/'
LOGIN_REDIRECT_URL = '/'

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

#: Userpics will be uploaded here.
USERPICS_PATH = pre.NETAPP_STORAGE + '/userpics'

MEDIA_ROOT = pre.NETAPP_STORAGE

# Userpics will accessed here.
USERPICS_URL = pre.UPLOAD_URL + '/userpics'

AUTH_PROFILE_MODULE = 'users.UserProfile'

MAX_PHOTO_UPLOAD_SIZE = 8 * (1024 ** 2)

AUTO_VOUCH_DOMAINS = ('mozilla.com', 'mozilla.org', 'mozillafoundation.org')
SOUTH_TESTS_MIGRATE = False

# Django-CSP
CSP_IMG_SRC = ("'self'", 'http://statse.webtrendslive.com',
               'https://statse.webtrendslive.com',
               'http://www.gravatar.com',
               'https://secure.gravatar.com',)
CSP_SCRIPT_SRC = ("'self'", 'http://statse.webtrendslive.com',
                  'https://statse.webtrendslive.com',
                  'https://browserid.org',)
CSP_REPORT_ONLY = True
CSP_REPORT_URI = '/csp/report'

ES_DISABLED = True
ES_HOSTS = ['127.0.0.1:9200']
ES_INDEXES = dict(default='mozillians')

# Use this to reserve the URL namespace
USERNAME_BLACKLIST = ('save', 'tofumatt', 'lonelyvegan', 'tag', 'group',
                      'about', 'groups', 'tags', 'media', 'username',
                      'register', 'new', 'delete', 'help', 'photo', 'img',
                      'src', 'files')

# Sorl settings
THUMBNAIL_DUMMY = True
THUMBNAIL_PREFIX = 'uploads/sorl-cache/'

# This is for the commons/helper.py thumbnail.
DEFAULT_IMAGE_SRC = path('./media/uploads/unknown.png')
