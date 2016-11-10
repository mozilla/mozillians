# -*- coding: utf-8 -*-

# Django settings for the mozillians project.
import logging
import os.path
import socket
import sys

from django.utils.functional import lazy

from django_jinja.builtins import DEFAULT_EXTENSIONS
from django_sha2 import get_password_hashers
from urlparse import urljoin


PROJECT_MODULE = 'mozillians'
ROOT_URLCONF = '%s.urls' % PROJECT_MODULE

DEV = False
DEBUG = False

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
path = lambda *a: os.path.abspath(os.path.join(ROOT, *a))  # noqa

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
TEXT_DOMAIN = 'django'
STANDALONE_DOMAINS = [TEXT_DOMAIN, 'djangojs']
LANGUAGE_CODE = 'en-US'
LOCALE_PATHS = [path('locale')]

# Tells the extract script what files to parse for strings and what functions to use.
PUENTE = {
    'BASE_DIR': ROOT,
    'DOMAIN_METHODS': {
        'django': [
            ('mozillians/**.py', 'python'),
            ('mozillians/**/templates/**.html', 'django'),
            ('mozillians/**/jinja2/**.html', 'jinja2')
        ]
    }
}


# Tells the product_details module where to find our local JSON files.
# This ultimately controls how LANGUAGES are constructed.
PROD_DETAILS_DIR = path('lib/product_details_json')

# Accepted locales
LANGUAGE_CODE = 'en-US'
PROD_LANGUAGES = ('ca', 'cs', 'de', 'en-US', 'en-GB', 'es', 'hu', 'fr', 'it', 'ko',
                  'nl', 'pl', 'pt-BR', 'pt-PT', 'ro', 'ru', 'sk', 'sl', 'sq', 'sr',
                  'sv-SE', 'te', 'zh-TW', 'zh-CN', 'lt', 'ja', 'hsb', 'dsb', 'uk', 'kab',)
DEV_LANGUAGES = PROD_LANGUAGES
CANONICAL_LOCALES = {
    'en': 'en-US',
}

# List of RTL locales known to this project. Subset of LANGUAGES.
RTL_LANGUAGES = ()  # ('ar', 'fa', 'fa-IR', 'he')


def get_langs():
    return DEV_LANGUAGES if DEV else PROD_LANGUAGES

LANGUAGE_URL_MAP = dict([(i.lower(), i) for i in get_langs()])


def lazy_langs():
    from product_details import product_details

    return dict([(lang.lower(), product_details.languages[lang]['native'])
                 for lang in get_langs() if lang in product_details.languages])

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

COMMON_CONTEXT_PROCESSORS = [
    'django.contrib.auth.context_processors.auth',
    'django.template.context_processors.debug',
    'django.template.context_processors.media',
    'django.template.context_processors.request',
    'django.template.context_processors.static',
    'django.template.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
    'session_csrf.context_processor',
    'mozillians.common.context_processors.i18n',
    'mozillians.common.context_processors.globals',
    'mozillians.common.context_processors.current_year',
    'mozillians.common.context_processors.canonical_path',
]

TEMPLATES = [
    {
        'BACKEND': 'django_jinja.backend.Jinja2',
        'DIRS': [path('mozillians/jinja2')],
        'NAME': 'jinja2',
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG,
            'app_dirname': 'jinja2',
            'match_extension': None,
            'newstyle_gettext': True,
            'undefined': 'jinja2.Undefined',
            'extensions': DEFAULT_EXTENSIONS + [
                'compressor.contrib.jinja2ext.CompressorExtension',
                'waffle.jinja.WaffleExtension',
                'puente.ext.i18n',
            ],
            'context_processors': COMMON_CONTEXT_PROCESSORS
        }
    },
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [path('mozillians/templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'debug': DEBUG,
            'context_processors': COMMON_CONTEXT_PROCESSORS
        }
    }
]


def COMPRESS_JINJA2_GET_ENVIRONMENT():
    from django.template import engines
    return engines['jinja2'].env

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

MIDDLEWARE_CLASSES = (
    'mozillians.common.middleware.LocaleURLMiddleware',
    'multidb.middleware.PinningRouterMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.security.SecurityMiddleware',

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

# Security middleware
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True

# Not all URLs need locale.
SUPPORTED_NONLOCALES = [
    'media',
    'static',
    'admin',
    'csp',
    'api',
    'contribute.json',
    'admin',
    'autocomplete',
    'humans.txt'
]

# Authentication settings
AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

USERNAME_MAX_LENGTH = 30

# On Login, we redirect through register.
LOGIN_URL = '/'
LOGIN_REDIRECT_URL = '/login/'

INSTALLED_APPS = (
    'dal',
    'dal_select2',

    # Django contrib apps
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'django.contrib.messages',
    'django.contrib.admin',

    # Third-party apps, patches, fixes
    'django_jinja',
    'djcelery',
    'puente',
    'compressor',
    'cronjobs',
    'commonware.response.cookies',
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
    'import_export',
    'waffle',
    'rest_framework',
    'raven.contrib.django.raven_compat',
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
CSP_REPORT_ONLY = False
CSP_REPORT_ENABLE = True
CSP_REPORT_URI = '/en-US/capture-csp-violation'
CSP_DEFAULT_SRC = (
    "'self'",
    'https://*.mapbox.com',
    'https://www.google.com/recaptcha/',
    'https://www.gstatic.com/recaptcha/',
)
CSP_FONT_SRC = (
    "'self'",
    'https://*.mozilla.net',
    'https://*.mozilla.org',
    'https://mozorg.cdn.mozilla.net',
)
CSP_CHILD_SRC = (
    "'self'",
)
CSP_IMG_SRC = (
    "'self'",
    'data:',
    'https://*.mozilla.net',
    'https://*.mozilla.org',
    '*.google-analytics.com',
    '*.gravatar.com',
    '*.wp.com',
    'https://*.mapbox.com',
)
CSP_SCRIPT_SRC = (
    "'self'",
    'https://www.mozilla.org',
    'https://*.mozilla.net',
    'https://*.google-analytics.com',
    'https://*.mapbox.com',
    'https://www.google.com/recaptcha/',
    'https://www.gstatic.com/recaptcha/',
)
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",
    'https://www.mozilla.org',
    'https://*.mozilla.net',
    'https://*.mapbox.com',
)
CSP_CHILD_SRC = (
    'https://www.google.com/recaptcha/',
)
CSP_FRAME_SRC = (
    'https://www.google.com/recaptcha/',
)

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

BASKET_VOUCHED_NEWSLETTER = 'mozilla-phone'
BASKET_NDA_NEWSLETTER = 'mozillians-nda'
NDA_GROUP = "nda"

USER_AVATAR_DIR = 'uploads/userprofile'
MOZSPACE_PHOTO_DIR = 'uploads/mozspaces'
ANNOUNCEMENTS_PHOTO_DIR = 'uploads/announcements'
ADMIN_EXPORT_MIXIN = 'mozillians.common.mixins.S3ExportMixin'

# Google Analytics
GA_ACCOUNT_CODE = 'UA-35433268-19'

# Akismet
AKISMET_API_KEY = ''

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
                         '^/api/']

# Set default avatar for user profiles
DEFAULT_AVATAR = 'img/default_avatar.png'
DEFAULT_AVATAR_URL = urljoin(MEDIA_URL, DEFAULT_AVATAR)
DEFAULT_AVATAR_PATH = os.path.join(MEDIA_ROOT, DEFAULT_AVATAR)

# Celery configuration
import djcelery  # noqa
djcelery.setup_loader()
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'

# True says to simulate background tasks without actually using celeryd.
# Good for local development in case celeryd is not running.
CELERY_ALWAYS_EAGER = True
BROKER_CONNECTION_TIMEOUT = 0.1
CELERY_RESULT_BACKEND = 'amqp'
CELERY_ACCEPT_CONTENT = ['pickle']
CELERY_TASK_RESULT_EXPIRES = 3600
CELERY_SEND_TASK_ERROR_EMAILS = True

# Time in seconds before celery.exceptions.SoftTimeLimitExceeded is raised.
# The task can catch that and recover but should exit ASAP.
CELERYD_TASK_SOFT_TIME_LIMIT = 150

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

SECRET_KEY = ''

USE_TZ = True

# Pagination: Items per page.
ITEMS_PER_PAGE = 24

COMPRESS_OFFLINE = True
COMPRESS_ENABLED = True

# Use custom CSS, JS compressors to enable SRI support
COMPRESS_CSS_COMPRESSOR = 'mozillians.common.compress.SRICssCompressor'
COMPRESS_JS_COMPRESSOR = 'mozillians.common.compress.SRIJsCompressor'


HUMANSTXT_GITHUB_REPO = 'https://api.github.com/repos/mozilla/mozillians/contributors'
HUMANSTXT_LOCALE_REPO = 'https://api.github.com/repos/mozilla-l10n/mozillians-l10n/contributors'
HUMANSTXT_FILE = os.path.join(STATIC_ROOT, 'humans.txt')
HUMANSTXT_URL = urljoin(STATIC_URL, 'humans.txt')

# These must both be set to a working mapbox token for the maps to work.
MAPBOX_MAP_ID = 'examples.map-zr0njcqy'
# This is the token for the edit profile page alone.
MAPBOX_PROFILE_ID = MAPBOX_MAP_ID

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

# Recaptcha
NORECAPTCHA_SITE_KEY = 'site_key'
NORECAPTCHA_SECRET_KEY = 'secret_key'
