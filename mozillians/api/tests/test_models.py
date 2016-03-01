from django.test import TestCase

from nose.tools import ok_

from mozillians.users.tests import UserFactory
from mozillians.api.models import APIApp


class APIAppTests(TestCase):
    def test_save_generates_key(self):
        owner = UserFactory.create()
        api_app = APIApp.objects.create(owner=owner, name='Test',
                                        description='Foo',
                                        key='')
        ok_(api_app.key != '')
