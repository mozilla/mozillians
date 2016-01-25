# -*- coding: utf-8 -*-

# Django settings for the mozillians project.
import logging
import os.path
import socket
import sys

from urlparse import urljoin

from django_sha2 import get_password_hashers

from django.utils.functional import lazy

PROJECT_MODULE = 'mozillians'
ROOT_URLCONF = '%s.urls' % PROJECT_MODULE

DEV = False
DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = ()
MANAGERS = ADMINS

# Site ID is used by Django's Sites framework.
SITE_ID = 1

# Log settings
LOG_LEVEL = logging.INFO
HAS_SYSLOG = True
LOGGING_CONFIG = None

SYSLOG_TAG = "http_app_mozillians"
LOGGING = {
    'loggers': {
        'landing': {'level': logging.INFO},
        'phonebook': {'level': logging.INFO},
    },
}

# Repository directory
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# path() bases things off of ROOT
path = lambda *a: os.path.abspath(os.path.join(ROOT, *a))

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

DATABASE_ROUTERS = ('multidb.PinningMasterSlaveRouter',)
SLAVE_DATABASES = []

# L10n
TIME_ZONE = 'America/Los_Angeles'
USE_I18N = True
USE_L10N = True
TEXT_DOMAIN = 'messages'
STANDALONE_DOMAINS = [TEXT_DOMAIN, 'javascript']
TOWER_KEYWORDS = {'_lazy': None}
TOWER_ADD_HEADERS = True
LANGUAGE_CODE = 'en-US'
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

# Tells the product_details module where to find our local JSON files.
# This ultimately controls how LANGUAGES are constructed.
PROD_DETAILS_DIR = path('lib/product_details_json')

# Accepted locales
LANGUAGE_CODE = 'en-US'
PROD_LANGUAGES = ('ca', 'cs', 'de', 'en-US', 'en-GB', 'es', 'hu', 'fr', 'it', 'ko',
                  'nl', 'pl', 'pt-BR', 'pt-PT', 'ro', 'ru', 'sk', 'sl', 'sq', 'sr',
                  'sv-SE', 'zh-TW', 'zh-CN', 'lt', 'ja', 'hsb', 'dsb', 'uk',)
DEV_LANGUAGES = ('en-US',)
CANONICAL_LOCALES = {
    'en': 'en-US',
}

# List of RTL locales known to this project. Subset of LANGUAGES.
RTL_LANGUAGES = ()  # ('ar', 'fa', 'fa-IR', 'he')


def lazy_lang_url_map():
    from django.conf import settings
    langs = settings.DEV_LANGUAGES if settings.DEV else settings.PROD_LANGUAGES
    return dict([(i.lower(), i) for i in langs])

LANGUAGE_URL_MAP = lazy(lazy_lang_url_map, dict)()


# Override Django's built-in with our native names
def lazy_langs():
    from django.conf import settings
    from product_details import product_details
    langs = DEV_LANGUAGES if settings.DEV else settings.PROD_LANGUAGES
    return dict([(lang.lower(), product_details.languages[lang]['native'])
                 for lang in langs if lang in product_details.languages])

LANGUAGES = lazy(lazy_langs, dict)()

# For absolute urls
try:
    DOMAIN = socket.gethostname()
except socket.error:
    DOMAIN = 'localhost'

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

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
    'session_csrf.context_processor',
    'django.contrib.messages.context_processors.messages',
    'mozillians.common.context_processors.i18n',
    'mozillians.common.context_processors.globals',
    'mozillians.common.context_processors.current_year',
    'mozillians.common.context_processors.canonical_path'
)

TEMPLATE_DIRS = (
    path('templates'),
)

# Absolute path to the directory that holds media.
MEDIA_ROOT = path('media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
STATIC_ROOT = path('static')

# URL prefix for static files.
STATIC_URL = '/static/'

# Storage of static files
COMPRESS_ROOT = STATIC_ROOT
COMPRESS_CSS_FILTERS = (
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.CSSMinFilter'
)
COMPRESS_PRECOMPILERS = (
    ('text/less', 'lessc {infile} {outfile}'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

JINGO_EXCLUDE_APPS = [
    'admin',
    'autocomplete_light',
    'browserid',
    'registration',
    'rest_framework',
]


def JINJA_CONFIG():
    config = {
        'extensions': [
            'tower.template.i18n',
            'jinja2.ext.do',
            'jinja2.ext.with_',
            'jinja2.ext.loopcontrols',
            'compressor.contrib.jinja2ext.CompressorExtension'
        ],
        'finalize': lambda x: x if x is not None else ''
    }
    return config


def COMPRESS_JINJA2_GET_ENVIRONMENT():
    from jingo import env
    return env


MIDDLEWARE_CLASSES = (
    'mozillians.common.middleware.LocaleURLMiddleware',
    'multidb.middleware.PinningRouterMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',

    'session_csrf.CsrfMiddleware',  # Must be after auth middleware.

    'django.contrib.messages.middleware.MessageMiddleware',

    'commonware.middleware.FrameOptionsHeader',
    'mobility.middleware.DetectMobileMiddleware',
    'mobility.middleware.XMobileMiddleware',
    'commonware.response.middleware.StrictTransportMiddleware',
    'csp.middleware.CSPMiddleware',
    'django_statsd.middleware.GraphiteMiddleware',
    'django_statsd.middleware.GraphiteRequestTimingMiddleware',

    'mozillians.common.middleware.StrongholdMiddleware',
    'mozillians.phonebook.middleware.RegisterMiddleware',
    'mozillians.phonebook.middleware.UsernameRedirectionMiddleware',
    'mozillians.groups.middleware.OldGroupRedirectionMiddleware',

    'waffle.middleware.WaffleMiddleware',
)

# Path to Java. Used for compress_assets.
JAVA_BIN = '/usr/bin/java'

# Sessions
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True

# StrictTransport
STS_SUBDOMAINS = True

# Not all URLs need locale.
SUPPORTED_NONLOCALES = [
    'media',
    'static',
    'admin',
    'csp',
    'api',
    'browserid',
    'contribute.json',
    'admin',
    'autocomplete',
    'humans.txt'
]

# Authentication settings
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
    'mozillians.common.authbackend.MozilliansAuthBackend'
)

USERNAME_MAX_LENGTH = 30

# On Login, we redirect through register.
LOGIN_URL = '/'
LOGIN_REDIRECT_URL = '/login/'

INSTALLED_APPS = (
    # Django contrib apps
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.messages',
    'django.contrib.admin',

    # Third-party apps, patches, fixes
    'compressor',
    'tower',
    'cronjobs',
    'django_browserid',
    'commonware.response.cookies',
    'djcelery',
    'django_nose',
    'session_csrf',
    'product_details',
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
    'import_export',
    'waffle',
    'rest_framework',
)

# Auth
BASE_PASSWORD_HASHERS = (
    'django_sha2.hashers.BcryptHMACCombinedPasswordVerifier',
    'django_sha2.hashers.SHA512PasswordHasher',
    'django_sha2.hashers.SHA256PasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.UnsaltedMD5PasswordHasher',
)

PWD_ALGORITHM = 'bcrypt'

HMAC_KEYS = {
    '2011-01-01': 'cheesecake',
}

PASSWORD_HASHERS = get_password_hashers(BASE_PASSWORD_HASHERS, HMAC_KEYS)

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

# Django-CSP
CSP_DEFAULT_SRC = ("'self'",
                   'http://*.mapbox.com',
                   'https://*.mapbox.com')
CSP_FONT_SRC = ("'self'",
                'http://*.mozilla.net',
                'https://*.mozilla.net',
                'http://*.mozilla.org',
                'https://*.mozilla.org',
                'https://mozorg.cdn.mozilla.net',
                'http://mozorg.cdn.mozilla.net')
CSP_CHILD_SRC = ("'self'",
                 'https://login.persona.org',)
CSP_IMG_SRC = ("'self'",
               'data:',
               'http://*.mozilla.net',
               'https://*.mozilla.net',
               'http://*.mozilla.org',
               'https://*.mozilla.org',
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
ES_URLS = ['http://127.0.0.1:9200']
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

# Celery configuration
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'

# True says to simulate background tasks without actually using celeryd.
# Good for local development in case celeryd is not running.
CELERY_ALWAYS_EAGER = True
BROKER_CONNECTION_TIMEOUT = 0.1
CELERY_RESULT_BACKEND = 'amqp'
CELERY_IGNORE_RESULT = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True

# Time in seconds before celery.exceptions.SoftTimeLimitExceeded is raised.
# The task can catch that and recover but should exit ASAP.
CELERYD_TASK_SOFT_TIME_LIMIT = 60 * 2

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
MAPBOX_MAP_ID = 'examples.map-zr0njcqy'
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

REST_FRAMEWORK = {
    'URL_FIELD_NAME': '_url',
    'PAGINATE_BY': 30,
    'MAX_PAGINATE_BY': 200,
    'DEFAULT_PERMISSION_CLASSES': (
        'mozillians.api.v2.permissions.MozilliansPermission',
    ),
    'DEFAULT_MODEL_SERIALIZER_CLASS':
        'rest_framework.serializers.HyperlinkedModelSerializer',
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework.filters.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
    ),
}

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# django-mobility
MOBILE_COOKIE = 'mobile'
