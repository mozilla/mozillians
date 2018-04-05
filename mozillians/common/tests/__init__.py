from __future__ import absolute_import

from contextlib import contextmanager, nested

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.test import TestCase as BaseTestCase
from django.test.client import Client
from django.test.utils import modify_settings, override_settings

from mock import patch
from nose.tools import make_decorator, ok_


AUTHENTICATION_BACKENDS = (
    'mozillians.common.tests.authentication.DummyAuthenticationBackend',
)
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
)
ES_INDEXES = {
    'default': 'mozillians-test',
    'public': 'mozillians-public-test'
}


@override_settings(AUTHENTICATION_BACKENDS=AUTHENTICATION_BACKENDS,
                   PASSWORD_HASHERS=PASSWORD_HASHERS)
@modify_settings(MIDDLEWARE={'remove': 'mozilla_django_oidc.middleware.RefreshIDToken'})
class TestCase(BaseTestCase):

    @contextmanager
    def login(self, user):
        client = Client()
        client.login(email=user.email)
        yield client


def requires_login():
    def decorate(func):
        def newfunc(*args, **kwargs):
            with nested(
                    patch('mozillians.common.middleware.messages.warning'),
                    patch('mozillians.common.middleware.login_required',
                          wraps=login_required)) as (messages_mock, login_mock):
                func(*args, **kwargs)
            ok_(messages_mock.called, 'messages.warning() was not called.')
            ok_(login_mock.called, 'login_required() was not called.')
        newfunc = make_decorator(func)(newfunc)
        return newfunc
    return decorate


def requires_vouch():
    def decorate(func):
        def newfunc(*args, **kwargs):
            with nested(
                    patch('mozillians.common.middleware.messages.error'),
                    patch('mozillians.common.middleware.redirect',
                          wraps=redirect)) as (messages_mock, redirect_mock):
                func(*args, **kwargs)
            ok_(messages_mock.called, 'messages.warning() was not called.')
            redirect_mock.assert_called_with('phonebook:home')
        newfunc = make_decorator(func)(newfunc)
        return newfunc
    return decorate
