from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test.utils import override_settings, override_script_prefix

from nose.tools import eq_

from mozillians.common.tests import (TestCase, requires_login, requires_vouch)
from mozillians.users.tests import UserFactory


@override_settings(ROOT_URLCONF='mozillians.common.tests.stronghold_urls')
class StrongholdTests(TestCase):
    """Stronghold Testcases."""

    def test_vouched_user_vouched_view(self):
        user = UserFactory.create()
        with override_script_prefix('/en-US/'):
            url = reverse('vouched')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')

    def test_vouched_user_unvouched_view(self):
        user = UserFactory.create()
        with override_script_prefix('/en-US/'):
            url = reverse('unvouched')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')

    def test_vouched_user_public_view(self):
        user = UserFactory.create()
        with override_script_prefix('/en-US/'):
            url = reverse('public')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')

    def test_vouched_user_excepted_view(self):
        user = UserFactory.create()
        with override_script_prefix('/en-US/'):
            url = reverse('excepted')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')

    @requires_vouch()
    def test_unvouched_user_vouched_view(self):
        user = UserFactory.create(vouched=False)
        with override_script_prefix('/en-US/'):
            url = reverse('vouched')
        with self.login(user) as client:
            client.get(url, follow=True)

    def test_unvouched_user_unvouched_view(self):
        user = UserFactory.create(vouched=False)
        with override_script_prefix('/en-US/'):
            url = reverse('unvouched')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')

    def test_unvouched_user_public_view(self):
        user = UserFactory.create(vouched=False)
        with override_script_prefix('/en-US/'):
            url = reverse('public')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')

    def test_unvouched_user_excepted_view(self):
        user = UserFactory.create(vouched=False)
        with override_script_prefix('/en-US/'):
            url = reverse('excepted')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')

    @requires_login()
    def test_anonymous_user_vouched_view(self):
        with override_script_prefix('/en-US/'):
            url = reverse('vouched')
        client = Client()
        client.get(url, follow=True)

    @requires_login()
    def test_anonymous_user_unvouched_view(self):
        with override_script_prefix('/en-US/'):
            url = reverse('unvouched')
        client = Client()
        client.get(url, follow=True)

    def test_anonymous_user_public_view(self):
        with override_script_prefix('/en-US/'):
            url = reverse('public')
        client = Client()
        response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')

    def test_anonymous_user_excepted_view(self):
        with override_script_prefix('/en-US/'):
            url = reverse('excepted')
        client = Client()
        response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')
