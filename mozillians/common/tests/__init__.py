from contextlib import contextmanager, nested

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.test.client import Client
from django.test.utils import override_settings

import factory
from mock import patch
from nose.tools import make_decorator, ok_
from test_utils import TestCase as BaseTestCase


AUTHENTICATION_BACKENDS =(
    'mozillians.common.tests.authentication.DummyAuthenticationBackend',
    )


@override_settings(AUTHENTICATION_BACKENDS=AUTHENTICATION_BACKENDS)
class TestCase(BaseTestCase):
    @contextmanager
    def login(self, user):
        client = Client()
        client.login(email=user.email)
        yield client


class UserFactory(factory.DjangoModelFactory):
    FACTORY_FOR = User
    username = factory.Sequence(lambda n: 'user{0}'.format(n))
    first_name = 'Joe'
    last_name = factory.Sequence(lambda n: 'Doe {0}'.format(n))
    email = factory.LazyAttribute(
        lambda a: '{0}.{1}@example.com'.format(a.first_name, a.last_name))

    @factory.post_generation
    def userprofile(self, create, extracted, **kwargs):
        self.userprofile.full_name = ' '.join([self.first_name, self.last_name])
        self.userprofile.country = 'gr'
        if extracted:
            for key, value in extracted.items():
                setattr(self.userprofile, key, value)
        self.userprofile.save()


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
            redirect_mock.assert_called_with('home')
        newfunc = make_decorator(func)(newfunc)
        return newfunc
    return decorate
