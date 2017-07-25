# -*- coding: utf-8 -*-

# Django settings for the mozillians project.
import json
import logging
import os.path
import sys

from django.utils.functional import lazy

from decouple import config, Csv
from unipath import Path
from dj_database_url import parse as db_url
from django_jinja.builtins import DEFAULT_EXTENSIONS
from django_sha2 import get_password_hashers
from urlparse import urljoin
from aws_requests_auth import boto_utils


PROJECT_MODULE = 'mozillians'
ROOT_URLCONF = '%s.urls' % PROJECT_MODULE

DEV = config('DEV', default=False, cast=bool)
DEBUG = config('DEBUG', default=False, cast=bool)

ADMIN_ALIAS = config('ADMIN_ALIAS', default='mozillians-admins@mozilla.com')
ADMINS = [('Mozillians.org Admins', ADMIN_ALIAS)],
MANAGERS = ADMINS

# Site ID is used by Django's Sites framework.
SITE_ID = 1

# Log settings
LOG_LEVEL = logging.INFO
HAS_SYSLOG = config('HAS_SYSLOG', default=True, cast=bool)
LOGGING_CONFIG = None

SYSLOG_TAG = config('SYSLOG_TAG', default="http_app_mozillians")
LOGGING = {
    'loggers': {
        'landing': {'level': logging.INFO},
        'phonebook': {'level': logging.INFO},
    },
}

# Repository directory
ROOT = Path(__file__).parent.parent

# Database settings
DATABASES = {
    'default': config('DATABASE_URL', cast=db_url)
}

DATABASE_ROUTERS = ('multidb.PinningMasterSlaveRouter',)
SLAVE_DATABASES = []

# L10n
TIME_ZONE = config('TIME_ZONE', default='America/Los_Angeles')
USE_I18N = config('USE_I18N', default=True, cast=bool)
USE_L10N = config('USE_L10N', default=True, cast=bool)
TEXT_DOMAIN = 'django'
STANDALONE_DOMAINS = [TEXT_DOMAIN, 'djangojs']
LANGUAGE_CODE = config('LANGUAGE_CODE', default='en-US')
LOCALE_PATHS = [Path('locale').resolve()]
# Accepted locales
PROD_LANGUAGES = ('ca', 'cs', 'de', 'en-US', 'en-GB', 'es', 'hu', 'fr', 'it', 'ko',
                  'nl', 'pl', 'pt-BR', 'pt-PT', 'ro', 'ru', 'sk', 'sl', 'sq', 'sr',
                  'sv-SE', 'te', 'zh-TW', 'zh-CN', 'lt', 'ja', 'hsb', 'dsb', 'uk', 'kab',
                  'fy-NL',)
DEV_LANGUAGES = PROD_LANGUAGES
CANONICAL_LOCALES = {
    'en': 'en-US',
}

EXEMPT_L10N_URLS = [
    '^/oidc/authenticate/',
    '^/oidc/callback/',
    '^/api/v1/',
    '^/api/v2/',
    '^/admin/'
]


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
PROD_DETAILS_DIR = Path(config('PROD_DETAILS_DIR', default='lib/product_details_json')).resolve()

# List of RTL locales known to this project. Subset of LANGUAGES.
RTL_LANGUAGES = ()  # ('ar', 'fa', 'fa-IR', 'he')


def get_langs():
    return DEV_LANGUAGES if DEV else PROD_LANGUAGES


LANGUAGE_URL_MAP = dict([(i.lower(), i) for i in get_langs()])


def lazy_langs():
    from product_details import product_details

    return [(lang.lower(), product_details.languages[lang]['native'])
            for lang in get_langs() if lang in product_details.languages]


LANGUAGES = lazy(lazy_langs, list)()

# For absolute urls
DOMAIN = config('DOMAIN', default='mozillians.org')
PROTOCOL = config('PROTOCOL', default='https://')
PORT = config('PORT', default=443, cast=int)
SITE_URL = config('SITE_URL', default='https://mozillians.org')

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
        'DIRS': [Path('mozillians/jinja2').resolve()],
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
        'DIRS': [Path('mozillians/templates').resolve()],
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
MEDIA_ROOT = Path('media').resolve()

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
MEDIA_URL = config('MEDIA_URL', default='/media/')

# Absolute path to the directory static files should be collected to.
STATIC_ROOT = Path('static').resolve()

# URL prefix for static files.
STATIC_URL = config('STATIC_URL', default='/static/')

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
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'mozillians.common.middleware.LocaleURLMiddleware',
    'multidb.middleware.PinningRouterMiddleware',

    'django.middleware.common.CommonMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'mozillians.common.middleware.HSTSPreloadMiddleware',  # Must be before security middleware
    'mozillians.common.middleware.ReferrerPolicyMiddleware',  # Must be before security middleware
    'django.middleware.security.SecurityMiddleware',

    'session_csrf.CsrfMiddleware',  # Must be after auth middleware.

    'django.contrib.messages.middleware.MessageMiddleware',

    'mobility.middleware.DetectMobileMiddleware',
    'mobility.middleware.XMobileMiddleware',
    'csp.middleware.CSPMiddleware',

    'mozillians.common.middleware.StrongholdMiddleware',
    'mozillians.phonebook.middleware.RegisterMiddleware',
    'mozillians.phonebook.middleware.UsernameRedirectionMiddleware',
    'mozillians.groups.middleware.OldGroupRedirectionMiddleware',

    'waffle.middleware.WaffleMiddleware',
)

X_FRAME_OPTIONS = config('X_FRAME_OPTIONS', default='DENY')

# Path to Java. Used for compress_assets.
JAVA_BIN = config('JAVA_BIN', default='/usr/bin/java')

# Sessions
SESSION_COOKIE_HTTPONLY = config('SESSION_COOKIE_HTTPONLY', default=True, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=True, cast=bool)
SESSION_COOKIE_NAME = config('SESSION_COOKIE_NAME', default='mozillians_sessionid')
ANON_ALWAYS = config('ANON_ALWAYS', default=True, cast=bool)

# Security middleware
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=True, cast=bool)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=31536000, cast=int)
ENABLE_HSTS_PRELOAD = config('ENABLE_HSTS_PRELOAD', default=True, cast=bool)
SECURE_CONTENT_TYPE_NOSNIFF = config('SECURE_CONTENT_TYPE_NOSNIFF', default=True, cast=bool)
SECURE_BROWSER_XSS_FILTER = config('SECURE_BROWSER_XSS_FILTER', default=True, cast=bool)
ENABLE_REFERRER_HEADER = config('ENABLE_REFERRER_HEADER', default=True, cast=bool)

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
    'mozillians.common.authbackend.MozilliansAuthBackend',
)

USERNAME_MAX_LENGTH = config('USERNAME_MAX_LENGTH', default=30, cast=int)

# On Login, we redirect through register.
LOGIN_URL = config('LOGIN_URL', default='/')
LOGIN_REDIRECT_URL = config('LOGIN_REDIRECT_URL', default='/login/')

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
    'django_nose',
    'session_csrf',
    'product_details',
    'csp',
    'mozilla_django_oidc',
    'cities_light',
    'axes',
    'haystack',

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

PWD_ALGORITHM = config('PWD_ALGORITHM', default='bcrypt')

HMAC_KEYS = {
    '2011-01-01': 'cheesecake',
}

PASSWORD_HASHERS = get_password_hashers(BASE_PASSWORD_HASHERS, HMAC_KEYS)

# Email
SERVER_EMAIL = config('SERVER_EMAIL', default='prod@mozillians.org')
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
FROM_NOREPLY = config('FROM_NOREPLY', default='Mozillians.org <no-reply@mozillians.org>')
FROM_NOREPLY_VIA = config('FROM_NOREPLY_VIA',
                          default='%s via Mozillians.org <noreply@mozillians.org>')

if EMAIL_BACKEND == 'django_ses.SESBackend':
    # Get AWS credentials from boto
    _aws_credentials = boto_utils.get_credentials()

    AWS_SES_REGION_NAME = config('AWS_SES_REGION_NAME',
                                 default='us-east-1')
    AWS_SES_REGION_ENDPOINT = config('AWS_SES_REGION_ENDPOINT',
                                     default='email.us-east-1.amazonaws.com')
    AWS_SES_ACCESS_KEY_ID = config('AWS_SES_ACCESS_KEY_ID',
                                   default=_aws_credentials['aws_access_key'])
    AWS_SES_SECRET_ACCESS_KEY = config('AWS_SES_SECRET_ACCESS_KEY',
                                       default=_aws_credentials['aws_secret_access_key'])
else:
    EMAIL_HOST = config('SMTP_EMAIL_HOST', default='localhost')
    EMAIL_PORT = config('SMTP_EMAIL_PORT', default='1025')
    EMAIL_HOST_USER = config('SMTP_EMAIL_HOST_USER', default='')
    EMAIL_HOST_PASSWORD = config('SMTP_EMAIL_HOST_PASSWORD', default='')

EMAIL_USE_TLS = config('SMTP_EMAIL_USE_TLS', default=False, cast=bool)

# Auth
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': config('CACHE_URL', default='127.0.0.1:11211'),
    }
}

MAX_PHOTO_UPLOAD_SIZE = 8 * (1024 ** 2)

AUTO_VOUCH_DOMAINS = (
    'mozilla.com',
    'mozilla.org',
    'mozillafoundation.org',
    'getpocket.com',
)
AUTO_VOUCH_REASON = 'An automatic vouch for being a Mozilla employee.'

# Django-CSP
CSP_REPORT_ONLY = config('CSP_REPORT_ONLY', default=False, cast=bool)
CSP_REPORT_ENABLE = config('CSP_REPORT_ENABLE', default=True, cast=bool)
CSP_REPORT_URI = config('CSP_REPORT_URI', default='/en-US/capture-csp-violation')
CSP_DEFAULT_SRC = (
    "'self'",
    'https://www.google.com/recaptcha/',
    'https://www.gstatic.com/recaptcha/',
)
CSP_FONT_SRC = (
    "'self'",
    'https://*.mozilla.net',
    'https://*.mozilla.org',
    'https://mozorg.cdn.mozilla.net',
)
CSP_IMG_SRC = (
    "'self'",
    'data:',
    'https://*.mozilla.net',
    'https://*.mozilla.org',
    '*.google-analytics.com',
    '*.gravatar.com',
    '*.wp.com',
    'https://*.mozillians.org',
)
CSP_SCRIPT_SRC = (
    "'self'",
    'https://www.mozilla.org',
    'https://*.mozilla.net',
    'https://*.google-analytics.com',
    'https://www.google.com/recaptcha/',
    'https://www.gstatic.com/recaptcha/',
)
CSP_STYLE_SRC = (
    "'self'",
    "'unsafe-inline'",
    'https://www.mozilla.org',
    'https://*.mozilla.net',
)
CSP_CHILD_SRC = (
    "'self'",
    'https://www.google.com/recaptcha/',
)

# Sorl settings
THUMBNAIL_DUMMY = config('THUMBNAIL_DUMMY', default=True, cast=bool)
THUMBNAIL_PREFIX = config('THUMBNAIL_PREFIX', default='uploads/sorl-cache/')

# Basket
# If we're running tests, don't hit the real basket server.
if 'test' in sys.argv:
    BASKET_URL = 'http://127.0.0.1'
else:
    # Basket requires SSL now for some calls
    BASKET_URL = config('BASKET_URL', default='https://basket.mozilla.com')

BASKET_VOUCHED_NEWSLETTER = config('BASKET_VOUCHED_NEWSLETTER', default='mozilla-phone')
BASKET_NDA_NEWSLETTER = config('BASKET_NDA_NEWSLETTER', default='mozillians-nda')
BASKET_API_KEY = config('BASKET_API_KEY')
NDA_GROUP = config('NDA_GROUP', default='nda')

USER_AVATAR_DIR = config('USER_AVATAR_DIR', default='uploads/userprofile')
MOZSPACE_PHOTO_DIR = config('MOZSPACE_PHOTO_DIR', default='uploads/mozspaces')
ANNOUNCEMENTS_PHOTO_DIR = config('ANNOUNCEMENTS_PHOTO_DIR', default='uploads/announcements')
ADMIN_EXPORT_MIXIN = config('ADMIN_EXPORT_MIXIN', default='mozillians.common.mixins.S3ExportMixin')

# Google Analytics
GA_ACCOUNT_CODE = config('GA_ACCOUNT_CODE', default='UA-35433268-19')

# Akismet
AKISMET_API_KEY = config('AKISMET_API_KEY', default='')

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default=DOMAIN, cast=Csv())

STRONGHOLD_EXCEPTIONS = ['^%s' % MEDIA_URL,
                         '^/csp/',
                         '^/admin/',
                         '^/api/',
                         '^/oidc/authenticate/',
                         '^/oidc/callback/',
                         # Allow autocomplete urls for profile registration
                         '^/[\w-]+/skills-autocomplete/',
                         '^/[\w-]+/country-autocomplete/',
                         '^/[\w-]+/city-autocomplete/',
                         '^/[\w-]+/region-autocomplete/',
                         '^/[\w-]+/timezone-autocomplete/']

# Set default avatar for user profiles
DEFAULT_AVATAR = config('DEFAULT_AVATAR', default='img/default_avatar.png')
DEFAULT_AVATAR_URL = config('DEFAULT_AVATAR_URL', default=urljoin(MEDIA_URL, DEFAULT_AVATAR))
DEFAULT_AVATAR_PATH = os.path.join(MEDIA_ROOT, DEFAULT_AVATAR)

# Celery configuration
import djcelery  # noqa
djcelery.setup_loader()
CELERYBEAT_SCHEDULER = config('CELERYBEAT_SCHEDULER',
                              default='djcelery.schedulers.DatabaseScheduler')

# True says to simulate background tasks without actually using celeryd.
# Good for local development in case celeryd is not running.
CELERY_ALWAYS_EAGER = config('CELERY_ALWAYS_EAGER', default='True', cast=bool)
BROKER_CONNECTION_TIMEOUT = config('BROKER_CONNECTION_TIMEOUT', default=0.1, cast=float)
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='amqp')
BROKER_URL = config('BROKER_URL', default='amqp://guest:guest@broker:5672//')
CELERY_ACCEPT_CONTENT = config('CELERY_ACCEPT_CONTENT', default='pickle', cast=Csv())
CELERY_TASK_RESULT_EXPIRES = config('CELERY_TASK_RESULT_EXPIRES', default=3600, cast=int)
CELERY_SEND_TASK_ERROR_EMAILS = config('CELERY_SEND_TASK_ERROR_EMAILS', default=True, cast=bool)
REDIS_CONNECT_RETRY = config('REDIS_CONNECT_RETRY',
                             default=CELERY_RESULT_BACKEND == 'redis', cast=bool)
# Time in seconds before celery.exceptions.SoftTimeLimitExceeded is raised.
# The task can catch that and recover but should exit ASAP.
CELERYD_TASK_SOFT_TIME_LIMIT = config('CELERYD_TASK_SOFT_TIME_LIMIT', default=150, cast=int)

MESSAGE_STORAGE = config('MESSAGE_STORAGE',
                         default='django.contrib.messages.storage.session.SessionStorage')

SECRET_KEY = config('SECRET_KEY', default='')

USE_TZ = config('USE_TZ', default=True, cast=bool)

# Pagination: Items per page.
ITEMS_PER_PAGE = config('ITEMS_PER_PAGE', default=24, cast=int)

COMPRESS_OFFLINE = config('COMPRESS_OFFLINE', default=True, cast=bool)
COMPRESS_ENABLED = config('COMPRESS_ENABLED', default=True, cast=bool)

# Use custom CSS, JS compressors to enable SRI support
COMPRESS_CSS_COMPRESSOR = 'mozillians.common.compress.SRICssCompressor'
COMPRESS_JS_COMPRESSOR = 'mozillians.common.compress.SRIJsCompressor'


HUMANSTXT_GITHUB_REPO = config(
    'HUMANSTXT_GITHUB_REPO',
    default='https://api.github.com/repos/mozilla/mozillians/contributors'
)
HUMANSTXT_LOCALE_REPO = config(
    'HUMANSTXT_LOCALE_REPO',
    default='https://api.github.com/repos/mozilla-l10n/mozillians-l10n/contributors'
)
HUMANSTXT_FILE = os.path.join(STATIC_ROOT, 'humans.txt')
HUMANSTXT_URL = urljoin(STATIC_URL, 'humans.txt')

# All accounts limited in 6 vouches total. Bug 997400.
VOUCH_COUNT_LIMIT = config('VOUCH_COUNT_LIMIT', default=6, cast=int)

# All accounts need 1 vouches to be able to vouch.
CAN_VOUCH_THRESHOLD = config('CAN_VOUCH_THRESHOLD', default=3, cast=int)

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
MOBILE_COOKIE = config('MOBILE_COOKIE', default='mobile')

# Recaptcha
NORECAPTCHA_SITE_KEY = config('NORECAPTCHA_SITE_KEY', default='site_key')
NORECAPTCHA_SECRET_KEY = config('NORECAPTCHA_SECRET_KEY', default='secret_key')


# Django OIDC

def _username_algo(email):
    from mozillians.common.authbackend import calculate_username
    return calculate_username(email)


OIDC_USERNAME_ALGO = _username_algo
OIDC_STORE_ACCESS_TOKEN = config('OIDC_STORE_ACCESS_TOKEN', default=True, cast=bool)
OIDC_RP_CLIENT_ID = config('OIDC_RP_CLIENT_ID', default='')
OIDC_RP_CLIENT_SECRET = config('OIDC_RP_CLIENT_SECRET', default='')
OIDC_RP_CLIENT_SECRET_ENCODED = config('OIDC_RP_CLIENT_SECRET_ENCODED', default=True, cast=bool)
OIDC_OP_DOMAIN = config('OIDC_OP_DOMAIN', default='auth.mozilla.auth0.com')
OIDC_OP_AUTHORIZATION_ENDPOINT = config('OIDC_OP_AUTHORIZATION_ENDPOINT', default='')
OIDC_OP_TOKEN_ENDPOINT = config('OIDC_OP_TOKEN_ENDPOINT', default='')
OIDC_OP_USER_ENDPOINT = config('OIDC_OP_USER_ENDPOINT', default='')

# AWS credentials
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID', default='')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY', default='')

# Django Haystack
ES_DISABLED = config('ES_DISABLED', default=True)
ES_HOST = config('ES_HOST', default='127.0.0.1:9200')
ES_PROTOCOL = config('ES_PROTOCOL', default='http://')


def _lazy_haystack_setup():
    from django.conf import settings

    es_url = '%s%s' % (settings.ES_PROTOCOL, settings.ES_HOST)
    es_index_name = config('ES_INDEX_NAME', default='mozillians_haystack')
    haystack_connections = {
        'default': {
            'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
            'URL': es_url,
            'INDEX_NAME': es_index_name
        },
        'tmp': {
            'ENGINE': 'haystack.backends.elasticsearch_backend.ElasticsearchSearchEngine',
            'URL': es_url,
            'INDEX_NAME': 'tmp_{}'.format(es_index_name)
        },
    }

    return haystack_connections


HAYSTACK_CONNECTIONS = lazy(_lazy_haystack_setup, dict)()
HAYSTACK_SIGNAL_PROCESSOR = 'mozillians.common.signals.SearchSignalProcessor'
ES_REINDEX_WORKERS_NUM = config('ES_REINDEX_WORKERS_NUM', default=10, cast=int)
ES_REINDEX_BATCHSIZE = config('ES_REINDEX_BATCHSIZE', default=100, cast=int)

# Setup django-axes
AXES_BEHIND_REVERSE_PROXY = True

# Setup sentry
RAVEN_CONFIG = config('RAVEN_CONFIG', cast=json.loads, default='{}')

# Mozillians Exports bucket
MOZILLIANS_ADMIN_BUCKET = config('MOZILLIANS_ADMIN_BUCKET', default='')

# Akismet
AKISMET_API_KEY = config('AKISMET_API_KEY', default='')

# Proxy configuration
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
