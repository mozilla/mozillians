from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponseNotAllowed
from django.test import Client

from mock import patch, call
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase, requires_login
from mozillians.users.models import UserProfile
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

    @patch('mozillians.users.models.remove_from_basket_task.delay')
    @patch('mozillians.users.models.unindex_objects.delay')
    def test_delete_unvouched(self, unindex_objects_mock,
                              remove_from_basket_task_mock):
        user = UserFactory.create(vouched=False, userprofile={'basket_token': 'token'})
        with self.login(user) as client:
            response = client.post(
                reverse('phonebook:profile_delete', prefix='/en-US/'),
                follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/home.html')

        remove_from_basket_task_mock.assert_called_with(
            user.email, user.userprofile.basket_token)
        unindex_objects_mock.assert_has_calls([
            call(UserProfile, [user.userprofile.id], public_index=False),
            call(UserProfile, [user.userprofile.id], public_index=True)
            ])
        ok_(not User.objects.filter(username=user.username).exists())

    @patch('mozillians.users.models.remove_from_basket_task.delay')
    @patch('mozillians.users.models.unindex_objects.delay')
    def test_delete_vouched(self, unindex_objects_mock,
                            remove_from_basket_task_mock):
        user = UserFactory.create(userprofile={'basket_token': 'token'})
        with self.login(user) as client:
            response = client.post(
                reverse('phonebook:profile_delete', prefix='/en-US/'),
                follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/home.html')

        remove_from_basket_task_mock.assert_called_with(
            user.email, user.userprofile.basket_token)
        unindex_objects_mock.assert_has_calls([
            call(UserProfile, [user.userprofile.id], public_index=False),
            call(UserProfile, [user.userprofile.id], public_index=True)
            ])
        ok_(not User.objects.filter(username=user.username).exists())
