from django.core.urlresolvers import reverse
from django.test.utils import override_script_prefix

from mock import patch
from nose.tools import eq_, ok_

from mozillians.api.models import APIv2App
from mozillians.api.tests import APIv2AppFactory
from mozillians.common.tests import TestCase
from mozillians.users.tests import UserFactory


class APIKeysTest(TestCase):

    def test_view_apikeys(self):
        user = UserFactory.create()

        with self.login(user) as client:
            url = reverse('phonebook:apikeys')
            response = client.get(url, follow=True)

        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/apikeys.html')

    def test_delete_apikey_invalid(self):
        user = UserFactory.create()
        key_owner = UserFactory.create()
        api_key = APIv2AppFactory.create(owner=key_owner.userprofile)

        with self.login(user) as client:
            url = reverse('phonebook:apikey_delete', kwargs={'api_pk': api_key.pk})
            response = client.get(url, follow=True)

        eq_(response.status_code, 404)

    @patch('mozillians.phonebook.views.messages.success')
    def test_delete_apikey_valid(self, success_mock):
        key_owner = UserFactory.create()
        api_key = APIv2AppFactory.create(owner=key_owner.userprofile)

        with self.login(key_owner) as client:
            url = reverse('phonebook:apikey_delete', kwargs={'api_pk': api_key.pk})
            response = client.get(url, follow=True)

        ok_(success_mock.called)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/apikeys.html')

    def test_request_apikey(self):
        user = UserFactory.create()
        with self.login(user) as client:
            with override_script_prefix('/en-US/'):
                url = reverse('phonebook:apikeys')
            data = {
                'url': 'http://example.com',
                'name': 'moomoo',
                'description': 'bar'
            }
            client.post(url, data)

        app_qs = APIv2App.objects.all()
        ok_(app_qs.exists())
        eq_(app_qs.count(), 1)
        eq_(app_qs[0].owner, user.userprofile)
