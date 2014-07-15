# -*- coding: utf-8 -*-

# Django settings for the mozillians project.
import logging
import os.path
import sys

from funfactory.manage import path
from funfactory.settings_base import *  # noqa
from funfactory.settings_base import JINJA_CONFIG as funfactory_JINJA_CONFIG
from urlparse import urljoin

from django.utils.functional import lazy

# Log settings
SYSLOG_TAG = "http_app_mozillians"
LOGGING = {
    'loggers': {
        'landing': {'level': logging.INFO},
        'phonebook': {'level': logging.INFO},
    },
}

# Database settings
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'HOST': '',
        'PORT': '',
        'OPTIONS': {
            'init_command': 'SET storage_engine=InnoDB',
            'charset': 'utf8',
            'use_unicode': True,
        },
        'TEST_CHARSET': 'utf8',
        'TEST_COLLATION': 'utf8_general_ci',
    },
}

# L10n
LOCALE_PATHS = [path('locale')]

# Tells the extract script what files to parse for strings and what functions to use.
DOMAIN_METHODS = {
    'messages': [
        ('mozillians/**.py',
            'tower.management.commands.extract.extract_tower_python'),
        ('mozillians/**/templates/**.html',
            'tower.management.commands.extract.extract_tower_template'),
        ('templates/**.html',
            'tower.management.commands.extract.extract_tower_template'),
    ],
}

# Accepted locales
LANGUAGE_CODE = 'en-US'
PROD_LANGUAGES = ('ca', 'cs', 'de', 'en-US', 'es', 'hu', 'fr', 'it', 'ko',
                  'nl', 'pl', 'pt-BR', 'ru', 'sk', 'sl', 'sq', 'sv', 'zh-TW',
                  'zh-CN', 'lt', 'ja')

# List of RTL locales known to this project. Subset of LANGUAGES.
RTL_LANGUAGES = ()  # ('ar', 'fa', 'fa-IR', 'he')

# For absoluate urls
PROTOCOL = "https://"
PORT = 443

# Templates.
# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'jingo.Loader',
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # 'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = get_template_context_processors(
    append=['mozillians.common.context_processors.current_year',
            'mozillians.common.context_processors.canonical_path'])


JINGO_EXCLUDE_APPS = [
    'admin',
    'autocomplete_light',
    'browserid'
]


def JINJA_CONFIG():
    config = funfactory_JINJA_CONFIG()
    config['extensions'].append('jingo_offline_compressor.jinja2ext.CompressorExtension')
    return config


MIDDLEWARE_CLASSES = get_middleware(append=[
    'commonware.response.middleware.StrictTransportMiddleware',
    'csp.middleware.CSPMiddleware',

    'django_statsd.middleware.GraphiteMiddleware',
    'django_statsd.middleware.GraphiteRequestTimingMiddleware',
    'django_statsd.middleware.TastyPieRequestTimingMiddleware',

    'mozillians.common.middleware.StrongholdMiddleware',
    'mozillians.phonebook.middleware.RegisterMiddleware',
    'mozillians.phonebook.middleware.UsernameRedirectionMiddleware',
    'mozillians.groups.middleware.OldGroupRedirectionMiddleware',

    'waffle.middleware.WaffleMiddleware',
])

# StrictTransport
STS_SUBDOMAINS = True

# Not all URLs need locale.
SUPPORTED_NONLOCALES = list(SUPPORTED_NONLOCALES) + [
    'csp',
    'api',
    'browserid',
    'admin',
    'autocomplete',
    'humans.txt'
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'mozillians.common.authbackend.MozilliansAuthBackend'
)

USERNAME_MAX_LENGTH = 30

# On Login, we redirect through register.
LOGIN_URL = '/'
LOGIN_REDIRECT_URL = '/login/'

INSTALLED_APPS = get_apps(append=[
    'csp',
    'mozillians',
    'mozillians.users',
    'mozillians.phonebook',
    'mozillians.groups',
    'mozillians.common',
    'mozillians.api',
    'mozillians.mozspaces',
    'mozillians.funfacts',
    'mozillians.announcements',
    'mozillians.humans',
    'mozillians.geo',

    'sorl.thumbnail',
    'autocomplete_light',

    'django.contrib.admin',
    'django_browserid',
    'jingo_offline_compressor',
    'import_export',
    'waffle',

    # DB migrations
    'south',
])

# Auth
PWD_ALGORITHM = 'bcrypt'
HMAC_KEYS = {
    '2011-01-01': 'cheesecake',
}

SESSION_COOKIE_HTTPONLY = True
SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_NAME = 'mozillians_sessionid'
ANON_ALWAYS = True

# Email
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
FROM_NOREPLY = u'Mozillians.org <no-reply@mozillians.org>'
FROM_NOREPLY_VIA = '%s via Mozillians.org <noreply@mozillians.org>'

# Auth
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
    }
}

MAX_PHOTO_UPLOAD_SIZE = 8 * (1024 ** 2)

AUTO_VOUCH_DOMAINS = ('mozilla.com', 'mozilla.org', 'mozillafoundation.org')
AUTO_VOUCH_REASON = 'An automatic vouch for being a Mozilla employee.'

SOUTH_TESTS_MIGRATE = False

# Django-CSP
CSP_DEFAULT_SRC = ("'self'",
                   'http://*.mapbox.com',
                   'https://*.mapbox.com')
CSP_FONT_SRC = ("'self'",
                'http://*.mozilla.net',
                'https://*.mozilla.net')
CSP_FRAME_SRC = ("'self'",
                 'https://login.persona.org',)
CSP_IMG_SRC = ("'self'",
               'data:',
               'http://*.mozilla.net',
               'https://*.mozilla.net',
               '*.google-analytics.com',
               '*.gravatar.com',
               '*.wp.com',
               'http://*.mapbox.com',
               'https://*.mapbox.com')
CSP_SCRIPT_SRC = ("'self'",
                  'http://www.mozilla.org',
                  'https://www.mozilla.org',
                  'http://*.mozilla.net',
                  'https://*.mozilla.net',
                  'https://*.google-analytics.com',
                  'https://login.persona.org',
                  'http://*.mapbox.com',
                  'https://*.mapbox.com')
CSP_STYLE_SRC = ("'self'",
                 "'unsafe-inline'",
                 'http://www.mozilla.org',
                 'https://www.mozilla.org',
                 'http://*.mozilla.net',
                 'https://*.mozilla.net',
                 'http://*.mapbox.com',
                 'https://*.mapbox.com')

# Elasticutils settings
ES_DISABLED = True
ES_HOSTS = ['127.0.0.1:9200']
ES_INDEXES = {'default': 'mozillians',
              'public': 'mozillians-public'}
ES_INDEXING_TIMEOUT = 10

# Sorl settings
THUMBNAIL_DUMMY = True
THUMBNAIL_PREFIX = 'uploads/sorl-cache/'

# Statsd Graphite
STATSD_CLIENT = 'django_statsd.clients.normal'

# Basket
# If we're running tests, don't hit the real basket server.
if 'test' in sys.argv:
    BASKET_URL = 'http://127.0.0.1'
else:
    # Basket requires SSL now for some calls
    BASKET_URL = 'https://basket.mozilla.com'
BASKET_NEWSLETTER = 'mozilla-phone'

USER_AVATAR_DIR = 'uploads/userprofile'
MOZSPACE_PHOTO_DIR = 'uploads/mozspaces'
ANNOUNCEMENTS_PHOTO_DIR = 'uploads/announcements'

# Google Analytics
GA_ACCOUNT_CODE = 'UA-35433268-19'

# Set ALLOWED_HOSTS based on SITE_URL.


def _allowed_hosts():
    from django.conf import settings
    from urlparse import urlparse

    host = urlparse(settings.SITE_URL).netloc  # Remove protocol and path
    host = host.rsplit(':', 1)[0]  # Remove port
    return [host]
ALLOWED_HOSTS = lazy(_allowed_hosts, list)()

STRONGHOLD_EXCEPTIONS = ['^%s' % MEDIA_URL,
                         '^/csp/',
                         '^/admin/',
                         '^/browserid/',
                         '^/api/']

# Set default avatar for user profiles
DEFAULT_AVATAR = 'img/default_avatar.png'
DEFAULT_AVATAR_URL = urljoin(MEDIA_URL, DEFAULT_AVATAR)
DEFAULT_AVATAR_PATH = os.path.join(MEDIA_ROOT, DEFAULT_AVATAR)

CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

SECRET_KEY = ''

USE_TZ = True

# Pagination: Items per page.
ITEMS_PER_PAGE = 24

COMPRESS_OFFLINE = True
COMPRESS_ENABLED = True

HUMANSTXT_GITHUB_REPO = 'https://api.github.com/repos/mozilla/mozillians/contributors'
HUMANSTXT_LOCALE_REPO = 'https://svn.mozilla.org/projects/l10n-misc/trunk/mozillians/locales'
HUMANSTXT_FILE = os.path.join(STATIC_ROOT, 'humans.txt')
HUMANSTXT_URL = urljoin(STATIC_URL, 'humans.txt')

# These must both be set to a working mapbox token for the maps to work.
MAPBOX_MAP_ID = 'examples.map-i86nkdio'
# This is the token for the edit profile page alone.
MAPBOX_PROFILE_ID = MAPBOX_MAP_ID


def _browserid_request_args():
    from django.conf import settings
    from tower import ugettext_lazy as _lazy

    args = {
        'siteName': _lazy('Mozillians'),
    }

    if settings.SITE_URL.startswith('https'):
        args['siteLogo'] = urljoin(STATIC_URL, "mozillians/img/apple-touch-icon-144.png")

    return args


def _browserid_audiences():
    from django.conf import settings
    return [settings.SITE_URL]

# BrowserID creates a user if one doesn't exist.
BROWSERID_CREATE_USER = True
BROWSERID_VERIFY_CLASS = 'mozillians.common.authbackend.BrowserIDVerify'
BROWSERID_REQUEST_ARGS = lazy(_browserid_request_args, dict)()
BROWSERID_AUDIENCES = lazy(_browserid_audiences, list)()

# All accounts limited in 6 vouches total. Bug 997400.
VOUCH_COUNT_LIMIT = 6

# All accounts need 1 vouches to be able to vouch.
CAN_VOUCH_THRESHOLD = 3
