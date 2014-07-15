from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.test import Client
from django.test.utils import override_settings

from funfactory.helpers import urlparams

from mock import patch
from nose.tools import ok_, eq_

from mozillians.common.helpers import redirect
from mozillians.common.tests import TestCase
from mozillians.users.managers import PUBLIC, MOZILLIANS, EMPLOYEES, PRIVILEGED
from mozillians.users.tests import UserFactory


class ViewProfileTests(TestCase):
    @patch('mozillians.phonebook.views.messages.warning')
    @patch('mozillians.phonebook.views.login_required', wraps=login_required)
    def test_view_profile_no_public_anonymous(self, login_required_mock,
                                              warning_mock):
        lookup_user = UserFactory.create()
        client = Client()
        url = reverse('phonebook:profile_view',
                      kwargs={'username': lookup_user.username})
        client.get(url, follow=True)
        ok_(warning_mock.called)
        ok_(login_required_mock.called)

    @patch('mozillians.phonebook.views.messages.error')
    @patch('mozillians.phonebook.views.redirect', wraps=redirect)
    def test_view_profile_no_public_unvouched(self, redirect_mock, error_mock):
        lookup_user = UserFactory.create()
        user = UserFactory.create(vouched=False)
        with self.login(user) as client:
            url = reverse('phonebook:profile_view',
                          kwargs={'username': lookup_user.username})
            client.get(url, follow=True)
        ok_(redirect_mock.called)
        ok_(error_mock.called)

    def test_view_profile_no_public_vouched(self):
        lookup_user = UserFactory.create()
        user = UserFactory.create()
        with self.login(user) as client:
            url = reverse('phonebook:profile_view',
                          kwargs={'username': lookup_user.username})
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], lookup_user)
        eq_(response.context['profile'], lookup_user.userprofile)

    def test_view_vouched_profile_public_anonymous(self):
        lookup_user = UserFactory.create(userprofile={'privacy_full_name': PUBLIC})
        client = Client()
        url = reverse('phonebook:profile_view',
                      kwargs={'username': lookup_user.username})
        response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], lookup_user)
        eq_(response.context['profile'], lookup_user.userprofile)
        eq_(response.context['profile']._privacy_level, PUBLIC)
        ok_('vouch_form' not in response.context)

    def test_view_vouched_profile_public_unvouched(self):
        lookup_user = UserFactory.create(userprofile={'privacy_full_name': PUBLIC})
        user = UserFactory.create(vouched=False)
        with self.login(user) as client:
            url = reverse('phonebook:profile_view',
                          kwargs={'username': lookup_user.username})
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], lookup_user)
        eq_(response.context['profile'], lookup_user.userprofile)
        eq_(response.context['profile']._privacy_level, PUBLIC)
        ok_('vouch_form' not in response.context)

    @override_settings(CAN_VOUCH_THRESHOLD=1)
    def test_view_vouched_profile_public_vouched(self):
        lookup_user = UserFactory.create(userprofile={'privacy_full_name': PUBLIC})
        user = UserFactory.create()
        with self.login(user) as client:
            url = reverse('phonebook:profile_view',
                          kwargs={'username': lookup_user.username})
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], lookup_user)
        eq_(response.context['profile'], lookup_user.userprofile)
        eq_(response.context['profile']._privacy_level, MOZILLIANS)
        ok_('vouch_form' in response.context)

    def test_view_unvouched_profile_public_anonymous(self):
        lookup_user = UserFactory.create(vouched=False,
                                         userprofile={'privacy_full_name': PUBLIC})
        client = Client()
        url = reverse('phonebook:profile_view',
                      kwargs={'username': lookup_user.username})
        response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], lookup_user)
        eq_(response.context['profile'], lookup_user.userprofile)
        eq_(response.context['profile']._privacy_level, PUBLIC)
        ok_('vouch_form' not in response.context)

    def test_view_unvouched_profile_public_unvouched(self):
        lookup_user = UserFactory.create(vouched=False,
                                         userprofile={'privacy_full_name': PUBLIC})
        user = UserFactory.create(vouched=False)
        with self.login(user) as client:
            url = reverse('phonebook:profile_view',
                          kwargs={'username': lookup_user.username})
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], lookup_user)
        eq_(response.context['profile'], lookup_user.userprofile)
        eq_(response.context['profile']._privacy_level, PUBLIC)
        ok_('vouch_form' not in response.context)

    @override_settings(CAN_VOUCH_THRESHOLD=1)
    def test_view_unvouched_profile_public_vouched(self):
        lookup_user = UserFactory.create(vouched=False,
                                         userprofile={'privacy_full_name': PUBLIC})
        user = UserFactory.create()
        with self.login(user) as client:
            url = reverse('phonebook:profile_view',
                          kwargs={'username': lookup_user.username})
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], lookup_user)
        eq_(response.context['profile'], lookup_user.userprofile)
        eq_(response.context['profile']._privacy_level, MOZILLIANS)
        ok_('vouch_form' in response.context)

    def test_view_profile_mine_unvouched(self):
        user = UserFactory.create(vouched=False)
        with self.login(user) as client:
            url = reverse('phonebook:profile_view',
                          kwargs={'username': user.username})
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], user)
        eq_(response.context['profile'], user.userprofile)
        eq_(response.context['profile']._privacy_level, None)
        eq_(response.context['privacy_mode'], 'myself')

    def test_view_profile_mine_vouched(self):
        user = UserFactory.create()
        with self.login(user) as client:
            url = reverse('phonebook:profile_view',
                          kwargs={'username': user.username})
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], user)
        eq_(response.context['profile'], user.userprofile)
        eq_(response.context['profile']._privacy_level, None)
        eq_(response.context['privacy_mode'], 'myself')

    def test_view_profile_mine_as_anonymous(self):
        user = UserFactory.create()
        url = reverse('phonebook:profile_view',
                      kwargs={'username': user.username})
        url = urlparams(url, view_as='anonymous')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], user)
        eq_(response.context['profile'], user.userprofile)
        eq_(response.context['profile']._privacy_level, PUBLIC)
        eq_(response.context['privacy_mode'], 'anonymous')

    def test_view_profile_mine_as_mozillian(self):
        user = UserFactory.create()
        url = reverse('phonebook:profile_view',
                      kwargs={'username': user.username})
        url = urlparams(url, view_as='mozillian')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], user)
        eq_(response.context['profile'], user.userprofile)
        eq_(response.context['profile']._privacy_level, MOZILLIANS)
        eq_(response.context['privacy_mode'], 'mozillian')

    def test_view_profile_mine_as_employee(self):
        user = UserFactory.create()
        url = reverse('phonebook:profile_view',
                      kwargs={'username': user.username})
        url = urlparams(url, view_as='employee')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], user)
        eq_(response.context['profile'], user.userprofile)
        eq_(response.context['profile']._privacy_level, EMPLOYEES)
        eq_(response.context['privacy_mode'], 'employee')

    def test_view_profile_mine_as_privileged(self):
        user = UserFactory.create()
        url = reverse('phonebook:profile_view',
                      kwargs={'username': user.username})
        url = urlparams(url, view_as='privileged')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], user)
        eq_(response.context['profile'], user.userprofile)
        eq_(response.context['profile']._privacy_level, PRIVILEGED)
        eq_(response.context['privacy_mode'], 'privileged')

    def test_view_profile_waiting_for_vouch_unvouched(self):
        unvouched_user = UserFactory.create(vouched=False)
        user = UserFactory.create(vouched=False)
        url = reverse('phonebook:profile_view',
                      kwargs={'username': unvouched_user.username})
        with self.login(user) as client:
            response = client.get(url, follow=True)
        ok_('vouch_form' not in response.context)

    @override_settings(CAN_VOUCH_THRESHOLD=1)
    def test_view_profile_waiting_for_vouch_vouched(self):
        unvouched_user = UserFactory.create(vouched=False)
        user = UserFactory.create()
        url = reverse('phonebook:profile_view',
                      kwargs={'username': unvouched_user.username})
        with self.login(user) as client:
            response = client.get(url, follow=True)
        ok_('vouch_form' in response.context)
