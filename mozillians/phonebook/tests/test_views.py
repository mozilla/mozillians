from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import logout as logout_view
from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest, HttpResponseNotAllowed
from django.test.client import Client

from funfactory.helpers import urlparams
from mock import Mock, call, patch
from nose.tools import eq_, ok_

from mozillians.common.helpers import redirect
from mozillians.common.tests import TestCase, requires_login, requires_vouch
from mozillians.phonebook.models import Invite
from mozillians.phonebook.tests import InviteFactory
from mozillians.phonebook.utils import update_invites
from mozillians.phonebook.views import BrowserIDVerify
from mozillians.users.managers import EMPLOYEES, MOZILLIANS, PRIVILEGED, PUBLIC
from mozillians.users.models import UserProfile
from mozillians.users.tests import UserFactory


class BrowserIDVerifyTests(TestCase):
    @patch('mozillians.phonebook.views.Verify.form_valid')
    def test_form_valid_anonymous(self, form_valid_mock):
        Verify = BrowserIDVerify()
        request_mock = Mock()
        request_mock.user.is_authenticated.return_value = False
        Verify.request = request_mock
        form = Mock()
        Verify.form_valid(form)
        form_valid_mock.assert_called_with(form)

    @patch('mozillians.phonebook.views.get_audience')
    @patch('mozillians.phonebook.views.verify')
    def test_form_valid_authenticated(self, verify_mock, get_audience_mock):
        user = UserFactory.create()
        Verify = BrowserIDVerify()
        request_mock = Mock()
        request_mock.user.is_authenticated.return_value = True
        request_mock.user = user
        Verify.request = request_mock
        form = Mock()
        form.cleaned_data = {'assertion': 'assertion'}
        get_audience_mock.return_value = 'audience'
        verify_mock.return_value = {'email': 'foo@bar.com'}

        Verify.form_valid(form)

        verify_mock.assert_called_with('assertion', 'audience')
        get_audience_mock.assert_called_with(request_mock)
        eq_(user.email, 'foo@bar.com')

    @patch('mozillians.phonebook.views.get_audience')
    @patch('mozillians.phonebook.views.verify')
    def test_form_valid_email_exists(self, verify_mock, get_audience_mock):
        UserFactory.create(email='foo@bar.com')
        user = UserFactory.create(email='la@example.com')
        Verify = BrowserIDVerify()
        request_mock = Mock()
        request_mock.user.is_authenticated.return_value = True
        request_mock.user = user
        Verify.request = request_mock
        form = Mock()
        form.cleaned_data = {'assertion': 'assertion'}
        get_audience_mock.return_value = 'audience'
        verify_mock.return_value = {'email': 'foo@bar.com'}

        Verify.form_valid(form)

        verify_mock.assert_called_with('assertion', 'audience')
        get_audience_mock.assert_called_with(request_mock)
        eq_(user.email, 'la@example.com')


class ViewsTests(TestCase):

    @requires_login()
    def test_login_anonymous(self):
        client = Client()
        client.get(reverse('phonebook:login'), follow=True)

    def test_login_unvouched(self):
        user = UserFactory.create()
        with self.login(user) as client:
            response = client.get(reverse('phonebook:login'), follow=True)
        self.assertTemplateUsed(response, 'phonebook/home.html')

    def test_login_vouched(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        with self.login(user) as client:
            response = client.get(reverse('phonebook:login'), follow=True)
        self.assertTemplateUsed(response, 'phonebook/home.html')

    def test_login_incomplete_profile(self):
        user = UserFactory.create(userprofile={'is_vouched': True,
         'full_name': ''})
        with self.login(user) as client:
            response = client.get(reverse('phonebook:login'), follow=True)
        self.assertTemplateUsed(response, 'phonebook/edit_profile.html')

    def test_home_anonymous(self):
        client = Client()
        response = client.get(reverse('phonebook:home'), follow=True)
        self.assertTemplateUsed(response, 'phonebook/home.html')
        ok_('profile' not in response.context)

    def test_home_unvouched(self):
        user = UserFactory.create()
        with self.login(user) as client:
            response = client.get(reverse('phonebook:home'), follow=True)
        self.assertTemplateUsed(response, 'phonebook/home.html')

    def test_home_vouched(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        with self.login(user) as client:
            response = client.get(reverse('phonebook:home'), follow=True)
        self.assertTemplateUsed(response, 'phonebook/home.html')

    @patch('mozillians.phonebook.views.messages.warning')
    @patch('mozillians.phonebook.views.login_required', wraps=login_required)
    def test_view_profile_no_public_anonymous(self, login_required_mock,
                                              warning_mock):
        lookup_user = UserFactory.create(userprofile={'is_vouched': True})
        client = Client()
        url = reverse('phonebook:profile_view',
                      kwargs={'username': lookup_user.username})
        client.get(url, follow=True)
        ok_(warning_mock.called)
        ok_(login_required_mock.called)

    @patch('mozillians.phonebook.views.messages.error')
    @patch('mozillians.phonebook.views.redirect', wraps=redirect)
    def test_view_profile_no_public_unvouched(self, redirect_mock, error_mock):
        lookup_user = UserFactory.create(userprofile={'is_vouched': True})
        user = UserFactory.create()
        with self.login(user) as client:
            url = reverse('phonebook:profile_view',
                          kwargs={'username': lookup_user.username})
            client.get(url, follow=True)
        ok_(redirect_mock.called)
        ok_(error_mock.called)

    def test_view_profile_no_public_vouched(self):
        lookup_user = UserFactory.create(userprofile={'is_vouched': True})
        user = UserFactory.create(userprofile={'is_vouched': True})
        with self.login(user) as client:
            url = reverse('phonebook:profile_view',
                          kwargs={'username': lookup_user.username})
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], lookup_user)
        eq_(response.context['profile'], lookup_user.userprofile)

    def test_view_vouched_profile_public_anonymous(self):
        lookup_user = UserFactory.create(userprofile={'is_vouched': True,
         'privacy_full_name': PUBLIC})
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
        lookup_user = UserFactory.create(userprofile={'is_vouched': True,
         'privacy_full_name': PUBLIC})
        user = UserFactory.create()
        with self.login(user) as client:
            url = reverse('phonebook:profile_view',
                          kwargs={'username': lookup_user.username})
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], lookup_user)
        eq_(response.context['profile'], lookup_user.userprofile)
        eq_(response.context['profile']._privacy_level, PUBLIC)
        ok_('vouch_form' not in response.context)

    def test_view_vouched_profile_public_vouched(self):
        lookup_user = UserFactory.create(userprofile={'is_vouched': True,
         'privacy_full_name': PUBLIC})
        user = UserFactory.create(userprofile={'is_vouched': True})
        with self.login(user) as client:
            url = reverse('phonebook:profile_view',
                          kwargs={'username': lookup_user.username})
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], lookup_user)
        eq_(response.context['profile'], lookup_user.userprofile)
        eq_(response.context['profile']._privacy_level, MOZILLIANS)
        ok_('vouch_form' not in response.context)

    def test_view_unvouched_profile_public_anonymous(self):
        lookup_user = UserFactory.create(
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
        lookup_user = UserFactory.create(
            userprofile={'privacy_full_name': PUBLIC})
        user = UserFactory.create()
        with self.login(user) as client:
            url = reverse('phonebook:profile_view',
                          kwargs={'username': lookup_user.username})
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], lookup_user)
        eq_(response.context['profile'], lookup_user.userprofile)
        eq_(response.context['profile']._privacy_level, PUBLIC)
        ok_('vouch_form' not in response.context)

    def test_view_unvouched_profile_public_vouched(self):
        lookup_user = UserFactory.create(
            userprofile={'privacy_full_name': PUBLIC})
        user = UserFactory.create(userprofile={'is_vouched': True})
        with self.login(user) as client:
            url = reverse('phonebook:profile_view',
                          kwargs={'username': lookup_user.username})
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], lookup_user)
        eq_(response.context['profile'], lookup_user.userprofile)
        eq_(response.context['profile']._privacy_level, MOZILLIANS)
        eq_(response.context['vouch_form'].initial['vouchee'],
            lookup_user.userprofile.id)

    def test_view_profile_mine_unvouched(self):
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

    def test_view_profile_mine_vouched(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
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
        user = UserFactory.create(userprofile={'is_vouched': True})
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
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('phonebook:profile_view',
                      kwargs={'username': user.username})
        url = urlparams(url,  view_as='mozillian')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['shown_user'], user)
        eq_(response.context['profile'], user.userprofile)
        eq_(response.context['profile']._privacy_level, MOZILLIANS)
        eq_(response.context['privacy_mode'], 'mozillian')

    def test_view_profile_mine_as_employee(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
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
        user = UserFactory.create(userprofile={'is_vouched': True})
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
        unvouched_user = UserFactory.create()
        user = UserFactory.create()
        url = reverse('phonebook:profile_view',
                      kwargs={'username': unvouched_user.username})
        with self.login(user) as client:
            response = client.get(url, follow=True)
        ok_('vouch_form' not in response.context)

    def test_view_profile_waiting_for_vouch_vouched(self):
        unvouched_user = UserFactory.create()
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('phonebook:profile_view',
                      kwargs={'username': unvouched_user.username})
        with self.login(user) as client:
            response = client.get(url, follow=True)
        ok_('vouch_form' in response.context)
        eq_(response.context['vouch_form'].initial['vouchee'],
            unvouched_user.userprofile.id)

    @requires_login()
    def test_confirm_delete_anonymous(self):
        client = Client()
        client.get(reverse('phonebook:profile_confirm_delete'), follow=True)

    def test_confirm_delete_unvouched(self):
        user = UserFactory.create()
        with self.login(user) as client:
            response = client.get(reverse('phonebook:profile_confirm_delete'),
                                  follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/confirm_delete.html')

    def test_confirm_delete_vouched(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        with self.login(user) as client:
            response = client.get(reverse('phonebook:profile_confirm_delete'),
                                  follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/confirm_delete.html')

    def test_delete_get_method(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
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
        user = UserFactory.create(userprofile={'basket_token': 'token'})
        with self.login(user) as client:
            response = client.post(
                reverse('phonebook:profile_delete', prefix='/en-US/'),
                follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/logout.html')

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
        self.assertTemplateUsed(response, 'phonebook/logout.html')

        remove_from_basket_task_mock.assert_called_with(
            user.email, user.userprofile.basket_token)
        unindex_objects_mock.assert_has_calls([
            call(UserProfile, [user.userprofile.id], public_index=False),
            call(UserProfile, [user.userprofile.id], public_index=True)
            ])
        ok_(not User.objects.filter(username=user.username).exists())

    def test_search_plugin_anonymous(self):
        client = Client()
        response = client.get(reverse('phonebook:search_plugin'), follow=True)
        eq_(response.status_code, 200)
        eq_(response.get('content-type'),
            'application/opensearchdescription+xml')

    def test_search_plugin_unvouched(self):
        user = UserFactory.create()
        with self.login(user) as client:
            response = client.get(reverse('phonebook:search_plugin'),
                                  follow=True)
        eq_(response.status_code, 200)
        eq_(response.get('content-type'),
            'application/opensearchdescription+xml')

    def test_search_plugin_vouched(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        with self.login(user) as client:
            response = client.get(reverse('phonebook:search_plugin'),
                                  follow=True)
        eq_(response.status_code, 200)
        eq_(response.get('content-type'),
            'application/opensearchdescription+xml')

    @requires_login()
    def test_invite_anonymous(self):
        client = Client()
        client.get(reverse('phonebook:invite'), follow=True)

    @requires_vouch()
    def test_invite_unvouched(self):
        user = UserFactory.create()
        with self.login(user) as client:
            client.get(reverse('phonebook:invite'), follow=True)

    def test_invite_get_vouched(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        with self.login(user) as client:
            response = client.get(reverse('phonebook:invite'), follow=True)
        self.assertTemplateUsed(response, 'phonebook/invite.html')

    @patch('mozillians.phonebook.views.messages.success')
    def test_invite_post_vouched(self, success_mock):
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('phonebook:invite', prefix='/en-US/')
        data = {'message': 'Join us foo!', 'recipient': 'foo@example.com'}
        with self.login(user) as client:
            response = client.post(url, data, follow=True)
        self.assertTemplateUsed(response, 'phonebook/home.html')
        ok_(Invite.objects
            .filter(recipient='foo@example.com', message='Join us foo!')
            .exists())
        ok_(success_mock.called)

    def test_invite_already_vouched(self):
        vouched_user = UserFactory.create(userprofile={'is_vouched': True})
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('phonebook:invite', prefix='/en-US/')
        data = {'recipient': vouched_user.email}
        with self.login(user) as client:
            response = client.post(url, data, follow=True)
        self.assertTemplateUsed(response, 'phonebook/invite.html')
        ok_('recipient' in response.context['invite_form'].errors)
        eq_(Invite.objects.all().count(), 0)

    def test_vouch_get_method(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('phonebook:vouch', prefix='/en-US/')
        with self.login(user) as client:
            response = client.get(url)
        ok_(isinstance(response, HttpResponseNotAllowed))

    @requires_login()
    def test_vouch_anonymous(self):
        client = Client()
        url = reverse('phonebook:vouch', prefix='/en-US/')
        client.post(url)

    @requires_vouch()
    def test_vouch_unvouched(self):
        user = UserFactory.create()
        url = reverse('phonebook:vouch', prefix='/en-US/')
        with self.login(user) as client:
            client.post(url)

    @patch('mozillians.phonebook.views.messages.info')
    def test_vouch_vouched(self, info_mock):
        user = UserFactory.create(userprofile={'is_vouched': True})
        unvouched_user = UserFactory.create()
        url = reverse('phonebook:vouch', prefix='/en-US/')
        data = {'vouchee': unvouched_user.userprofile.id}
        with self.login(user) as client:
            response = client.post(url, data, follow=True)
        unvouched_user = User.objects.get(id=unvouched_user.id)
        self.assertTemplateUsed(response, 'phonebook/profile.html')
        eq_(response.context['profile'], unvouched_user.userprofile)
        ok_(unvouched_user.userprofile.is_vouched)
        ok_(info_mock.called)

    def test_vouch_invalid_form_vouched(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('phonebook:vouch', prefix='/en-US/')
        data = {'vouchee': 'invalid'}
        with self.login(user) as client:
            response = client.post(url, data, follow=True)
        ok_(isinstance(response, HttpResponseBadRequest))

    @requires_login()
    def test_list_mozillians_in_location_anonymous(self):
        client = Client()
        url = reverse('phonebook:list_country', kwargs={'country': 'gr'})
        client.get(url, follow=True)

    @requires_vouch()
    def test_list_mozillians_in_location_unvouched(self):
        user = UserFactory.create()
        with self.login(user) as client:
            url = reverse('phonebook:list_country', kwargs={'country': 'gr'})
            client.get(url, follow=True)

    def test_list_mozillians_in_location_country_vouched(self):
        user_listed = UserFactory.create(userprofile={'is_vouched': True,
         'country': 'it'})
        UserFactory.create(userprofile={'is_vouched': True})
        UserFactory.create()
        UserFactory.create(userprofile={'country': 'gr'})
        user = UserFactory.create(userprofile={'is_vouched': True})
        with self.login(user) as client:
            url = reverse('phonebook:list_country', kwargs={'country': 'it'})
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/location-list.html')
        eq_(response.context['country_name'], 'Italy')
        eq_(response.context['city_name'], None)
        eq_(response.context['region_name'], None)
        eq_(response.context['people'].count(), 1)
        eq_(response.context['people'][0], user_listed.userprofile)

    def test_list_mozillians_in_location_region_vouched(self):
        user_listed = UserFactory.create(userprofile={'is_vouched': True,
         'country': 'it',
         'region': 'florence'})
        UserFactory.create(userprofile={'is_vouched': True,
         'country': 'it',
         'region': 'foo'})
        UserFactory.create(userprofile={'is_vouched': True})
        UserFactory.create()
        UserFactory.create(userprofile={'country': 'gr'})
        user = UserFactory.create(userprofile={'is_vouched': True})
        with self.login(user) as client:
            url = reverse('phonebook:list_region', kwargs={'country': 'it',
             'region': 'Florence'})
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/location-list.html')
        eq_(response.context['country_name'], 'Italy')
        eq_(response.context['city_name'], None)
        eq_(response.context['region_name'], 'Florence')
        eq_(response.context['people'].count(), 1)
        eq_(response.context['people'][0], user_listed.userprofile)

    def test_list_mozillians_in_location_city_vouched(self):
        user_listed = UserFactory.create(userprofile={'is_vouched': True,
         'country': 'it',
         'city': 'madova'})
        UserFactory.create(userprofile={'is_vouched': True,
         'country': 'it',
         'city': 'foo'})
        UserFactory.create(userprofile={'is_vouched': True})
        UserFactory.create()
        UserFactory.create(userprofile={'country': 'gr'})
        user = UserFactory.create(userprofile={'is_vouched': True})
        with self.login(user) as client:
            url = reverse('phonebook:list_city', kwargs={'country': 'it',
             'city': 'Madova'})
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/location-list.html')
        eq_(response.context['country_name'], 'Italy')
        eq_(response.context['city_name'], 'Madova')
        eq_(response.context['region_name'], None)
        eq_(response.context['people'].count(), 1)
        eq_(response.context['people'][0], user_listed.userprofile)

    def test_list_mozillians_in_location_region_n_city_vouched(self):
        user_listed = UserFactory.create(userprofile={'is_vouched': True,
         'country': 'it',
         'region': 'Florence',
         'city': 'madova'})
        UserFactory.create(userprofile={'is_vouched': True,
         'country': 'it',
         'region': 'florence',
         'city': 'foo'})
        UserFactory.create(userprofile={'is_vouched': True})
        UserFactory.create()
        UserFactory.create(userprofile={'country': 'gr'})
        user = UserFactory.create(userprofile={'is_vouched': True})
        with self.login(user) as client:
            url = reverse('phonebook:list_region_city', kwargs={'country': 'it',
             'region': 'florence',
             'city': 'Madova'})
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/location-list.html')
        eq_(response.context['country_name'], 'Italy')
        eq_(response.context['city_name'], 'Madova')
        eq_(response.context['region_name'], 'florence')
        eq_(response.context['people'].count(), 1)
        eq_(response.context['people'][0], user_listed.userprofile)

    def test_list_mozillians_in_location_invalid_country(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        with self.login(user) as client:
            url = reverse('phonebook:list_country',
                          kwargs={'country': 'invalid'})
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/location-list.html')
        eq_(response.context['country_name'], 'invalid')
        eq_(response.context['city_name'], None)
        eq_(response.context['region_name'], None)
        eq_(response.context['people'].count(), 0)

    @requires_login()
    def test_logout_anonymous(self):
        client = Client()
        client.get(reverse('phonebook:logout'), follow=True)

    @patch('mozillians.phonebook.views.auth.views.logout', wraps=logout_view)
    def test_logout_unvouched(self, logout_mock):
        user = UserFactory.create()
        with self.login(user) as client:
            response = client.get(reverse('phonebook:logout'), follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/logout.html')
        ok_(logout_mock.called)

    @patch('mozillians.phonebook.views.auth.views.logout', wraps=logout_view)
    def test_logout_vouched(self, logout_mock):
        user = UserFactory.create(userprofile={'is_vouched': True})
        with self.login(user) as client:
            response = client.get(reverse('phonebook:logout'), follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/logout.html')
        ok_(logout_mock.called)

    def test_register_anonymous(self):
        client = Client()
        url = urlparams(reverse('phonebook:register'), code='foo')
        response = client.get(url, follow=True)
        eq_(client.session['invite-code'], 'foo')
        self.assertTemplateUsed(response, 'phonebook/home.html')

    @patch('mozillians.phonebook.views.update_invites',
           wraps=update_invites)
    def test_register_unvouched(self, update_invites_mock):
        user = UserFactory.create()
        invite = InviteFactory.create(inviter=user.userprofile)
        url = urlparams(reverse('phonebook:register'), code=invite.code)
        with self.login(user) as client:
            response = client.get(url, follow=True)
        user = User.objects.get(id=user.id)
        ok_(user.userprofile.is_vouched)
        ok_(update_invites_mock.called)
        self.assertTemplateUsed(response, 'phonebook/home.html')

    @patch('mozillians.phonebook.views.update_invites',
           wraps=update_invites)
    def test_register_vouched(self, update_invites_mock):
        voucher_1 = UserFactory.create(userprofile={'is_vouched': True})
        voucher_2 = UserFactory.create(userprofile={'is_vouched': True})
        user = UserFactory.create(
            userprofile={'is_vouched': True,
                         'vouched_by': voucher_1.userprofile})
        invite = InviteFactory.create(inviter=voucher_2.userprofile)
        url = urlparams(reverse('phonebook:register'), code=invite.code)
        with self.login(user) as client:
            response = client.get(url, follow=True)
        user = User.objects.get(id=user.id)
        ok_(user.userprofile.is_vouched)
        ok_(user.userprofile.vouched_by, voucher_1.userprofile)
        ok_(not update_invites_mock.called)
        self.assertTemplateUsed(response, 'phonebook/home.html')

    def test_register_without_code_anonymous(self):
        client = Client()
        response = client.get(reverse('phonebook:register'), follow=True)
        ok_(not self.client.session.get('invite-code'))
        self.assertTemplateUsed(response, 'phonebook/home.html')
        eq_(response.status_code, 200)

    def test_register_without_code_unvouched(self):
        user = UserFactory.create()
        with self.login(user) as client:
            response = client.get(reverse('phonebook:register'), follow=True)
        ok_(not self.client.session.get('invite-code'))
        self.assertTemplateUsed(response, 'phonebook/home.html')
        eq_(response.status_code, 200)

    def test_register_without_code_vouched(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        with self.login(user) as client:
            response = client.get(reverse('phonebook:register'), follow=True)
        ok_(not self.client.session.get('invite-code'))
        self.assertTemplateUsed(response, 'phonebook/home.html')
        eq_(response.status_code, 200)

    @patch('mozillians.phonebook.views.forms.ProfileForm')
    def test_email_change_verification_redirection(self, profile_form_mock):
        profile_form_mock().is_valid.return_value = True
        user = UserFactory.create(email='old@example.com',
                                  userprofile={'is_vouched': True})
        data = {'full_name': 'foobar',
                'email': 'new@example.com',
                'country': 'gr',
                'username': user.username,
                'externalaccount_set-MAX_NUM_FORMS': '1000',
                'externalaccount_set-INITIAL_FORMS': '0',
                'externalaccount_set-TOTAL_FORMS': '0'}
        url = reverse('phonebook:profile_edit', prefix='/en-US/')
        with self.login(user) as client:
            response = client.post(url, data=data, follow=True)
        self.assertTemplateUsed(response, 'phonebook/verify_email.html')
        eq_(user.email, 'old@example.com')
