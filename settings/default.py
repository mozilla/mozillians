# -*- coding: utf-8 -*-

# Django settings for the mozillians project.
import ldap
import logging

from django_auth_ldap.config import _LDAPConfig, LDAPSearch

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
TEMPLATE_DIRS = (path('apps/users/templates'), )

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'jingo.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (base.TEMPLATE_CONTEXT_PROCESSORS +
    ('django_browserid.context_processors.browserid_form',))

JINGO_EXCLUDE_APPS = [
    'admin',
]

MINIFY_BUNDLES = {
    'css': {
        'common': (
            'css/jquery-ui-1.8.16.custom.css',
            'js/libs/tag-it/css/jquery.tagit.css',
            'css/mozilla-base.css',
            'css/main.css',
        ),
    },
    'js': {
        'common': (
            'js/libs/jquery-1.4.4.min.js',
            'js/libs/jquery-ui-1.8.7.custom.min.js',
            'js/libs/tag-it/js/tag-it.js',
            'js/libs/validation/validation.js',
            'js/main.js',
            'js/browserid.js',
            'js/groups.js',
        ),
    }
}

MIDDLEWARE_CLASSES = list(base.MIDDLEWARE_CLASSES) + [
    'commonware.response.middleware.StrictTransportMiddleware',
    'commonware.response.middleware.GraphiteMiddleware',
    'commonware.response.middleware.GraphiteRequestTimingMiddleware',
    'csp.middleware.CSPMiddleware',
    'phonebook.middleware.PermissionDeniedMiddleware',
    # 'larper.middleware.LarperMiddleware',
]

# StrictTransport
STS_SUBDOMAINS = True

# OpenLDAP
LDAP_USERS_GROUP = 'ou=people,dc=mozillians,dc=org'

AUTHENTICATION_BACKENDS = ('django_browserid.auth.BrowserIDBackend',)

#BrowserID creates useer if one doesn't exist
BROWSERID_CREATE_USER = True

#On Login, we redirect through register
LOGIN_REDIRECT_URL = '/register'

AUTH_LDAP_USER_SEARCH = LDAPSearch(LDAP_USERS_GROUP, ldap.SCOPE_SUBTREE,
                                   "(uid=%(user)s)")
AUTH_LDAP_USER_ATTR_MAP = {"first_name": "cn", "last_name": "sn",
                           "email": "mail"}
AUTH_LDAP_PROFILE_ATTR_MAP = {"home_directory": "homeDirectory",
                              "unique_id": "uniqueIdentifier",
                              "phone": "telephoneNumber:",
                              "voucher": "mozilliansVouchedBy"}
AUTH_LDAP_ALWAYS_UPDATE_USER = False

INSTALLED_APPS = list(base.INSTALLED_APPS) + [
    #These need to go in order of migration
    'users',
    'phonebook',
    'groups',
    'taskboard',
    # 'locations',
    'larper',

    'csp',
    'jingo_minify',
    'tower',
    'cronjobs',

    'django.contrib.admin',
    'django.contrib.auth',
    'django_browserid',

    # DB migrations
    'south',
    # re-assert dominance of 'django_nose'
    'django_nose',

]

## Auth
PWD_ALGORITHM = 'bcrypt'
HMAC_KEYS = {
    '2011-01-01': 'cheesecake',
}

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

#: Userpics will accessed here.
USERPICS_URL = pre.UPLOAD_URL + '/userpics'

AUTH_PROFILE_MODULE = 'users.UserProfile'

MAX_PHOTO_UPLOAD_SIZE = 8 * (1024 ** 2)

AUTO_VOUCH_DOMAINS = ('mozilla.com', 'mozilla.org', 'mozillafoundation.org')
SOUTH_TESTS_MIGRATE = False

# Django-CSP
CSP_IMG_SRC = ("'self'", 'http://statse.webtrendslive.com',
               'https://statse.webtrendslive.com',)
CSP_SCRIPT_SRC = ("'self'", 'http://statse.webtrendslive.com',
                  'https://statse.webtrendslive.com',)
CSP_REPORT_ONLY = True
CSP_REPORT_URI = '/csp/report'

ES_DISABLED = True
ES_HOSTS = ['127.0.0.1:9200']
ES_INDEXES = dict(default='mozillians')

# Use this to reserve the URL namespace
USERNAME_BLACKLIST = ('save', 'tofumatt', 'tag', 'group', 'groups', 'tags',
                      'media', 'username', 'register', 'new', 'delete',
                      'help', 'photo', 'img', 'src', 'files')
