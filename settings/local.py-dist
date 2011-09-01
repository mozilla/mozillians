# This is an example settings_local.py file.
# Copy it and add your local settings here.

from settings import *

# For absoluate urls
DOMAIN = "localhost"
PROTOCOL = "http://"
PORT = 8001

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'mozillians',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
        'OPTIONS': {
            'init_command': 'SET storage_engine=InnoDB',
            'charset' : 'utf8',
            'use_unicode' : True,
        },
        'TEST_CHARSET': 'utf8',
        'TEST_COLLATION': 'utf8_general_ci',
    },
}

#### OpenLDAP ####
# Read/Write Master slapd
LDAP_SYNC_PROVIDER_URI = "ldap://localhost:1389"
# Read only mirror or load balancer
LDAP_SYNC_CONSUMER_URI = LDAP_SYNC_PROVIDER_URI

# Admin account
LDAP_ADMIN_DN = 'uid=LDAPAdmin,ou=accounts,ou=system,dc=mozillians,dc=org'
LDAP_ADMIN_PASSWORD = 'secret'

# Registrar account
LDAP_REGISTRAR_DN = 'uid=regAgent,ou=accounts,ou=system,dc=mozillians,dc=org'
LDAP_REGISTRAR_PASSWORD = 'secret'

#### django-auth-ldap ####
AUTH_LDAP_SERVER_URI = LDAP_SYNC_CONSUMER_URI

# Simple bind user
AUTH_LDAP_BIND_DN = ""
AUTH_LDAP_BIND_PASSWORD = ""




ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DEBUG = TEMPLATE_DEBUG = True
