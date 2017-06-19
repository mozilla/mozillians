from django.contrib.auth.models import AnonymousUser
from django.test.client import RequestFactory
from django.utils.timezone import now

from mock import patch
from nose.tools import ok_

from mozillians.api.models import APIv2App
from mozillians.api.tests import APIv2AppFactory
from mozillians.api.v2.permissions import MozilliansPermission
from mozillians.common.tests import TestCase
from mozillians.users.tests import UserFactory


class MozilliansPermissionTests(TestCase):

    def test_has_permission_valid_key(self):
        class DummyClass(object):
            pass
        view = DummyClass()
        timestamp = now()

        user = UserFactory.create()
        app = APIv2AppFactory.create(owner=user.userprofile)
        request_factory = RequestFactory()
        request = request_factory.get('/', data={'api-key': app.key})
        request.user = AnonymousUser()
        mozillians_permission = MozilliansPermission()

        with patch('mozillians.api.v2.permissions.now') as now_mock:
            now_mock.return_value = timestamp
            ok_(mozillians_permission.has_permission(request, view))

        ok_(APIv2App.objects.filter(id=app.id, last_used=timestamp).exists())

    def test_has_permission_no_key(self):
        request = RequestFactory().request()
        request.user = AnonymousUser()
        mozillians_permission = MozilliansPermission()
        ok_(not mozillians_permission.has_permission(request, '/'))

    def test_has_permission_invalid_key(self):
        request_factory = RequestFactory()
        request = request_factory.get('/', data={'api-key': 'foo'})
        request.user = AnonymousUser()
        mozillians_permission = MozilliansPermission()
        ok_(not mozillians_permission.has_permission(request, '/'))

    def test_has_permission_assigned_key(self):
        class DummyClass(object):
            pass
        view = DummyClass()
        request_factory = RequestFactory()
        request = request_factory.get('/')
        user = UserFactory.create()
        app = APIv2AppFactory.create(owner=user.userprofile)
        timestamp = now()
        request.user = user
        mozillians_permission = MozilliansPermission()

        with patch('mozillians.api.v2.permissions.now') as now_mock:
            now_mock.return_value = timestamp
            ok_(mozillians_permission.has_permission(request, view))
        ok_(APIv2App.objects.filter(id=app.id, last_used=timestamp).exists())
