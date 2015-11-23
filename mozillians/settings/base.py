# -*- coding: utf-8 -*-

# Django settings for the mozillians project.
import logging
import os.path
import sys
from urlparse import urljoin

from django.utils.functional import lazy


DEV = False
DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = ()
MANAGERS = ADMINS

DATABASES = {}  # See settings_local.

SLAVE_DATABASES = []

DATABASE_ROUTERS = ('multidb.PinningMasterSlaveRouter',)

# Site ID is used by Django's Sites framework.
SITE_ID = 1


# CEF Logging
CEF_PRODUCT = 'Mozillians'
CEF_VENDOR = 'Mozilla'
CEF_VERSION = '0'
CEF_DEVICE_VERSION = '0'


# Internationalization.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Gettext text domain
TEXT_DOMAIN = 'messages'
STANDALONE_DOMAINS = [TEXT_DOMAIN, 'javascript']
TOWER_KEYWORDS = {'_lazy': None}
TOWER_ADD_HEADERS = True

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-US'

# Accepted locales

# Tells the product_details module where to find our local JSON files.
# This ultimately controls how LANGUAGES are constructed.
# Log settings
HAS_SYSLOG = True
LOG_LEVEL = logging.INFO
SYSLOG_TAG = "http_app_mozillians"
LOGGING_CONFIG = None
LOGGING = {
    'loggers': {
        'landing': {'level': logging.INFO},
        'phonebook': {'level': logging.INFO},
    },
}

DEV_LANGUAGES = None
CANONICAL_LOCALES = {
    'en': 'en-US',
}


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
SLAVE_DATABASES = []

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

ROOT = os.path.dirname(os.path.dirname(__file__))
ROOT_URLCONF = '%s.urls' % os.path.basename(ROOT)

# path bases things off of ROOT
path = lambda *a: os.path.abspath(os.path.join(ROOT, *a))

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

# Tells the product_details module where to find our local JSON files.
# This ultimately controls how LANGUAGES are constructed.
PROD_DETAILS_DIR = path('../lib/product_details_json')
# Accepted locales
LANGUAGE_CODE = 'en-US'
PROD_LANGUAGES = ('ca', 'cs', 'de', 'en-US', 'en-GB', 'es', 'hu', 'fr', 'it', 'ko',
                  'nl', 'pl', 'pt-BR', 'pt-PT', 'ro', 'ru', 'sk', 'sl', 'sq', 'sr',
                  'sv-SE', 'zh-TW', 'zh-CN', 'lt', 'ja', 'hsb', 'dsb', 'uk',)

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


JINGO_EXCLUDE_APPS = [
    'admin',
    'autocomplete_light',
    'browserid',
    'rest_framework',
]


def JINJA_CONFIG():
    config = {'extensions': ['tower.template.i18n',
                             'jinja2.ext.do',
                             'jinja2.ext.with_',
                             'jinja2.ext.loopcontrols',
                             'compressor.contrib.jinja2ext.CompressorExtension'],
              'finalize': lambda x: x if x is not None else ''}
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
    'django_statsd.middleware.TastyPieRequestTimingMiddleware',
    'mozillians.common.middleware.StrongholdMiddleware',
    'mozillians.phonebook.middleware.RegisterMiddleware',
    'mozillians.phonebook.middleware.UsernameRedirectionMiddleware',
    'mozillians.groups.middleware.OldGroupRedirectionMiddleware',
    'waffle.middleware.WaffleMiddleware',
)

# StrictTransport
STS_SUBDOMAINS = True

# Not all URLs need locale.
SUPPORTED_NONLOCALES = [
    'media',
    'static',
    'admin'
    'csp',
    'api',
    'browserid',
    'contribute.json',
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

INSTALLED_APPS = (
    'funfactory',
    'compressor',
    'tower',
    'cronjobs',
    'django_browserid',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
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
    'django.contrib.admin',
    'import_export',
    'waffle',
    'rest_framework'
)

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

# Django-CSP
CSP_DEFAULT_SRC = ("'self'",
                   'http://*.mapbox.com',
                   'https://*.mapbox.com')
CSP_FONT_SRC = ("'self'",
                'http://*.mozilla.net',
                'https://*.mozilla.net',
                'http://*.mozilla.org',
                'https://*.mozilla.org')
CSP_FRAME_SRC = ("'self'",
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

MEDIA_ROOT = path('media')
MEDIA_URL = '/media/'
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

STATIC_ROOT = path('static')
STATIC_URL = '/static/'

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
