from django.core.urlresolvers import reverse
from django.test.client import Client

from nose.tools import eq_

from mozillians.common.tests import (TestCase, UserFactory,
                                     requires_login, requires_vouch)


class StrongholdTests(TestCase):
    """Stronghold Testcases."""
    urls = 'mozillians.common.tests.stronghold_urls'

    def test_vouched_user_vouched_view(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('vouched', prefix='/en-US/')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')

    def test_vouched_user_unvouched_view(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('unvouched', prefix='/en-US/')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')

    def test_vouched_user_public_view(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('public', prefix='/en-US/')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')

    def test_vouched_user_excepted_view(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('excepted', prefix='/en-US/')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')

    @requires_vouch()
    def test_unvouched_user_vouched_view(self):
        user = UserFactory.create()
        url = reverse('vouched', prefix='/en-US/')
        with self.login(user) as client:
            client.get(url, follow=True)

    def test_unvouched_user_unvouched_view(self):
        user = UserFactory.create()
        url = reverse('unvouched', prefix='/en-US/')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')

    def test_unvouched_user_public_view(self):
        user = UserFactory.create()
        url = reverse('public', prefix='/en-US/')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')

    def test_unvouched_user_excepted_view(self):
        user = UserFactory.create()
        url = reverse('excepted', prefix='/en-US/')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')

    @requires_login()
    def test_anonymous_user_vouched_view(self):
        url = reverse('vouched', prefix='/en-US/')
        client = Client()
        client.get(url, follow=True)

    @requires_login()
    def test_anonymous_user_unvouched_view(self):
        url = reverse('unvouched', prefix='/en-US/')
        client = Client()
        client.get(url, follow=True)

    def test_anonymous_user_public_view(self):
        url = reverse('public', prefix='/en-US/')
        client = Client()
        response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')

    def test_anonymous_user_excepted_view(self):
        url = reverse('excepted', prefix='/en-US/')
        client = Client()
        response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.content, 'Hi!')
