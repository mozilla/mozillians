from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseNotAllowed
from django.test import Client
from django.test.utils import override_settings

from mock import patch, call
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase, requires_login
from mozillians.users.es import UserProfileMappingType
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
        with self.login(user) as client:
            response = client.get(
                reverse('phonebook:profile_delete', prefix='/en-US/'),
                follow=True)
        ok_(isinstance(response, HttpResponseNotAllowed))

    @requires_login()
    def test_delete_anonymous(self):
        client = Client()
        client.post(reverse('phonebook:profile_delete'), follow=True)

    @patch('mozillians.users.models.unsubscribe_from_basket_task.delay')
    @patch('mozillians.users.models.unindex_objects.delay')
    def test_delete_unvouched(self, unindex_objects_mock,
                              unsubscribe_from_basket_task_mock):
        user = UserFactory.create(vouched=False, userprofile={'basket_token': 'token'})
        with self.login(user) as client:
            response = client.post(
                reverse('phonebook:profile_delete', prefix='/en-US/'),
                follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/home.html')

        unsubscribe_from_basket_task_mock.assert_called_with(
            user.email, user.userprofile.basket_token)
        unindex_objects_mock.assert_has_calls([
            call(UserProfileMappingType, [user.userprofile.id], public_index=False),
            call(UserProfileMappingType, [user.userprofile.id], public_index=True)])
        ok_(not User.objects.filter(username=user.username).exists())

    @patch('mozillians.users.models.unsubscribe_from_basket_task.delay')
    @patch('mozillians.users.models.unindex_objects.delay')
    def test_delete_vouched(self, unindex_objects_mock,
                            unsubscribe_from_basket_task_mock):
        user = UserFactory.create(userprofile={'basket_token': 'token'})
        with self.login(user) as client:
            response = client.post(
                reverse('phonebook:profile_delete', prefix='/en-US/'),
                follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/home.html')

        unsubscribe_from_basket_task_mock.assert_called_with(
            user.email, user.userprofile.basket_token)
        unindex_objects_mock.assert_has_calls([
            call(UserProfileMappingType, [user.userprofile.id], public_index=False),
            call(UserProfileMappingType, [user.userprofile.id], public_index=True)])
        ok_(not User.objects.filter(username=user.username).exists())

    @override_settings(AUTO_VOUCH_DOMAINS=['example.com'])
    @override_settings(AUTO_VOUCH_REASON='Autovouch reason')
    def test_delete_auto_vouch_domain(self):
        user = UserFactory.create(email='foo@example.com')
        description = 'Autovouch reason'
        vouch = user.userprofile.vouches_received.filter(autovouch=True, description=description)
        ok_(vouch.exists())

        with self.login(user) as client:
            response = client.post(
                reverse('phonebook:profile_delete', prefix='/en-US/'),
                follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/home.html')
