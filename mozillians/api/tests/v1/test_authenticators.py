from django.test.client import RequestFactory

from nose.tools import eq_, ok_
from test_utils import TestCase

from mozillians.api.v1.authenticators import AppAuthentication
from mozillians.api.tests import APIAppFactory


class AppAuthenticationTests(TestCase):
    def test_valid_app(self):
        app = APIAppFactory.create()
        request = RequestFactory()
        request.GET = {'app_key': app.key, 'app_name': app.name}
        authentication = AppAuthentication()
        ok_(authentication.is_authenticated(request))

    def test_empty_app_name(self):
        app = APIAppFactory.create()
        request = RequestFactory()
        request.GET = {'app_key': app.key}
        authentication = AppAuthentication()
        eq_(authentication.is_authenticated(request), False)

    def test_empty_app_key(self):
        app = APIAppFactory.create()
        request = RequestFactory()
        request.GET = {'app_name': app.name}
        authentication = AppAuthentication()
        eq_(authentication.is_authenticated(request), False)

    def test_invalid_app_name(self):
        app = APIAppFactory.create()
        request = RequestFactory()
        request.GET = {'app_key': app.key, 'app_name': 'invalid'}
        authentication = AppAuthentication()
        eq_(authentication.is_authenticated(request), False)

    def test_invalid_app_key(self):
        app = APIAppFactory.create()
        request = RequestFactory()
        request.GET = {'app_key': 'invalid', 'app_name': app.name}
        authentication = AppAuthentication()
        eq_(authentication.is_authenticated(request), False)

    def test_invalid_app_name_and_key(self):
        request = RequestFactory()
        request.GET = {'app_key': 'invalid', 'app_name': 'invalid'}
        authentication = AppAuthentication()
        eq_(authentication.is_authenticated(request), False)

    def test_mozilla_app(self):
        app = APIAppFactory.create(is_mozilla_app=True)
        request = RequestFactory()
        request.GET = {'app_key': app.key, 'app_name': app.name}
        authentication = AppAuthentication()
        authentication.is_authenticated(request)
        eq_(request.GET.get('restricted'), None)

    def test_community_app(self):
        app = APIAppFactory.create(is_mozilla_app=False)
        request = RequestFactory()
        request.GET = {'app_key': app.key, 'app_name': app.name}
        authentication = AppAuthentication()
        authentication.is_authenticated(request)
        eq_(request.GET.get('restricted'), True)
