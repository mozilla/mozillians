from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseNotAllowed
from django.test import Client
from django.test.utils import override_settings, override_script_prefix

from mock import patch
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase, requires_login
from mozillians.users.tests import UserFactory


class DeleteTests(TestCase):
    @requires_login()
    def test_confirm_delete_anonymous(self):
        client = Client()
        client.get(reverse('phonebook:profile_confirm_delete'), follow=True)

    def test_confirm_delete_unvouched(self):
        user = UserFactory.create(vouched=False)
        with self.login(user) as client:
            response = client.get(reverse('phonebook:profile_confirm_delete'),
                                  follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/confirm_delete.html')

    def test_confirm_delete_vouched(self):
        user = UserFactory.create()
        with self.login(user) as client:
            response = client.get(reverse('phonebook:profile_confirm_delete'),
                                  follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/confirm_delete.html')

    def test_delete_get_method(self):
        user = UserFactory.create()

        with override_script_prefix('/en-US'):
            url = reverse('phonebook:profile_delete')

        with self.login(user) as client:
            response = client.get(url, follow=True)
        ok_(isinstance(response, HttpResponseNotAllowed))

    @requires_login()
    def test_delete_anonymous(self):
        client = Client()
        client.post(reverse('phonebook:profile_delete'), follow=True)

    @patch('mozillians.users.signals.unsubscribe_from_basket_task.delay')
    @override_settings(BASKET_VOUCHED_NEWSLETTER='newsletter1')
    @override_settings(BASKET_NDA_NEWSLETTER='newsletter2')
    def test_delete_unvouched(self, unsubscribe_from_basket_task_mock):
        user = UserFactory.create(vouched=False)
        with override_script_prefix('/en-US/'):
            url = reverse('phonebook:profile_delete')

        with self.login(user) as client:
            response = client.post(url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/home.html')

        unsubscribe_from_basket_task_mock.assert_called_with(user.email,
                                                             ['newsletter1', 'newsletter2'])

        ok_(not User.objects.filter(username=user.username).exists())

    @patch('mozillians.users.signals.unsubscribe_from_basket_task.delay')
    @override_settings(BASKET_VOUCHED_NEWSLETTER='newsletter1')
    @override_settings(BASKET_NDA_NEWSLETTER='newsletter2')
    def test_delete_vouched(self, unsubscribe_from_basket_task_mock):
        user = UserFactory.create()
        with override_script_prefix('/en-US/'):
            url = reverse('phonebook:profile_delete')
        with self.login(user) as client:
            response = client.post(url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/home.html')

        # This mock call needs assert_called_any beacuse it's called twice,
        # once from the pre_delete signal and once from the post_save signal
        # from the User creation.
        unsubscribe_from_basket_task_mock.assert_any_call(user.email,
                                                          ['newsletter1', 'newsletter2'])

        ok_(not User.objects.filter(username=user.username).exists())

    @override_settings(AUTO_VOUCH_DOMAINS=['example.com'])
    @override_settings(AUTO_VOUCH_REASON='Autovouch reason')
    def test_delete_auto_vouch_domain(self):
        user = UserFactory.create(email='foo@example.com')
        description = 'Autovouch reason'
        vouch = user.userprofile.vouches_received.filter(autovouch=True, description=description)
        ok_(vouch.exists())
        with override_script_prefix('/en-US/'):
            url = reverse('phonebook:profile_delete')

        with self.login(user) as client:
            response = client.post(url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/home.html')
