import json
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test.utils import override_settings, override_script_prefix

from mock import ANY, Mock, patch
from nose.tools import eq_

from mozillians.common.tests import TestCase
from mozillians.users.models import IdpProfile
from mozillians.users.tests import UserFactory


class EditProfileIdentities(TestCase):

    @override_settings(OIDC_OP_TOKEN_ENDPOINT='https://server.example.com/token')
    @override_settings(OIDC_OP_USER_ENDPOINT='https://server.example.com/user')
    @override_settings(OIDC_RP_VERIFICATION_CLIENT_ID='example_id')
    @override_settings(OIDC_RP_VERIFICATION_CLIENT_SECRET='client_secret')
    def setUp(self):
        self.url = reverse('phonebook:verify_identity_callback')
        self.get_data = {
            'code': 'code',
            'state': 'state'
        }

    @patch('mozillians.phonebook.views.messages')
    @patch('mozillians.phonebook.views.requests.post')
    @patch('mozillians.phonebook.views.jws.verify')
    def test_add_new_identity_non_mfa(self, verify_mock, request_post_mock, msg_mock):
        """Test adding a new identity in a profile."""
        user = UserFactory.create(email='foo@example.com')
        verify_mock.return_value = json.dumps({
            'email': 'bar@example.com',
            'email_verified': True,
            'sub': 'email|'
        })
        post_json_mock = Mock()
        post_json_mock.json.return_value = {
            'id_token': 'id_token'
        }
        with self.login(user) as client:
            session = client.session
            session['oidc_verify_nonce'] = 'nonce'
            session['oidc_verify_state'] = 'state'
            session.save()
            response = client.get(self.url, self.get_data, follow=True)
            new_idp_profile = IdpProfile.objects.get(email='bar@example.com')
            eq_(new_idp_profile.primary, False)
            msg = 'Account successfully verified.'
            msg_mock.success.assert_called_once_with(ANY, msg)
            with override_script_prefix('/en-US/'):
                url = reverse('phonebook:profile_edit')
            self.assertRedirects(response, url)

    @patch('mozillians.phonebook.views.messages')
    @patch('mozillians.phonebook.views.requests.post')
    @patch('mozillians.phonebook.views.jws.verify')
    def test_add_new_identity_mfa(self, verify_mock, request_post_mock, msg_mock):
        """Test adding a new identity in a profile."""
        user = UserFactory.create(email='foo@example.com')
        verify_mock.return_value = json.dumps({
            'email': 'bar@example.com',
            'email_verified': True,
            'sub': 'ad|'
        })
        post_json_mock = Mock()
        post_json_mock.json.return_value = {
            'id_token': 'id_token'
        }
        with self.login(user) as client:
            session = client.session
            session['oidc_verify_nonce'] = 'nonce'
            session['oidc_verify_state'] = 'state'
            session.save()
            response = client.get(self.url, self.get_data, follow=True)
            new_idp_profile = IdpProfile.objects.get(email='bar@example.com')
            eq_(new_idp_profile.primary, True)
            msg = ('Account successfully verified. You need to use this identity '
                   'the next time you will login.')
            msg_mock.success.assert_called_once_with(ANY, msg)
            with override_script_prefix('/en-US/'):
                url = reverse('phonebook:profile_edit')
            self.assertRedirects(response, url)

    @patch('mozillians.phonebook.views.messages')
    @patch('mozillians.phonebook.views.requests.post')
    @patch('mozillians.phonebook.views.jws.verify')
    def test_add_new_identity_change_primary(self, verify_mock, request_post_mock, msg_mock):
        """Test adding a stronger identity and changing the primary email."""
        user = UserFactory.create(email='foo@example.com')
        IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='email|',
            email=user.email,
            primary=True
        )

        verify_mock.return_value = json.dumps({
            'email': 'bar@example.com',
            'email_verified': True,
            'sub': 'ad|ldap'
        })
        post_json_mock = Mock()
        post_json_mock.json.return_value = {
            'id_token': 'id_token'
        }
        with self.login(user) as client:
            session = client.session
            session['oidc_verify_nonce'] = 'nonce'
            session['oidc_verify_state'] = 'state'
            session.save()
            response = client.get(self.url, self.get_data, follow=True)
            old_idp_profile = IdpProfile.objects.get(email='foo@example.com')
            new_idp_profile = IdpProfile.objects.get(email='bar@example.com')
            eq_(old_idp_profile.primary, False)
            eq_(new_idp_profile.primary, True)
            user = User.objects.get(pk=user.pk)
            eq_(user.email, 'bar@example.com')
            msg = ('Account successfully verified. You need to use this identity '
                   'the next time you will login.')
            msg_mock.success.assert_called_once_with(ANY, msg)
            with override_script_prefix('/en-US/'):
                url = reverse('phonebook:profile_edit')
            self.assertRedirects(response, url)

    @patch('mozillians.phonebook.views.messages')
    @patch('mozillians.phonebook.views.requests.post')
    @patch('mozillians.phonebook.views.jws.verify')
    def test_email_not_verified(self, verify_mock, request_post_mock, msg_mock):
        user = UserFactory.create(email='foo@example.com')
        verify_mock.return_value = json.dumps({
            'email': 'bar@example.com',
            'email_verified': False,
            'sub': 'ad|ldap'
        })
        post_json_mock = Mock()
        post_json_mock.json.return_value = {
            'id_token': 'id_token'
        }
        with self.login(user) as client:
            session = client.session
            session['oidc_verify_nonce'] = 'nonce'
            session['oidc_verify_state'] = 'state'
            session.save()
            response = client.get(self.url, self.get_data, follow=True)
            msg = 'Account verification failed: Email is not verified.'
            msg_mock.error.assert_called_once_with(ANY, msg)
            with override_script_prefix('/en-US/'):
                url = reverse('phonebook:profile_edit')
            self.assertRedirects(response, url)

    @patch('mozillians.phonebook.views.messages')
    @patch('mozillians.phonebook.views.requests.post')
    @patch('mozillians.phonebook.views.jws.verify')
    def test_identity_exists(self, verify_mock, request_post_mock, msg_mock):
        user = UserFactory.create(email='foo@example.com')
        IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='email|',
            email=user.email,
            primary=True
        )

        verify_mock.return_value = json.dumps({
            'email': 'foo@example.com',
            'email_verified': True,
            'sub': 'email|'
        })
        post_json_mock = Mock()
        post_json_mock.json.return_value = {
            'id_token': 'id_token'
        }
        with self.login(user) as client:
            session = client.session
            session['oidc_verify_nonce'] = 'nonce'
            session['oidc_verify_state'] = 'state'
            session.save()
            response = client.get(self.url, self.get_data, follow=True)
            msg = 'Account verification failed: Identity already exists.'
            msg_mock.error.assert_called_once_with(ANY, msg)
            with override_script_prefix('/en-US/'):
                url = reverse('phonebook:profile_edit')
            self.assertRedirects(response, url)

    @patch('mozillians.phonebook.views.messages')
    @patch('mozillians.phonebook.views.requests.post')
    @patch('mozillians.phonebook.views.jws.verify')
    def test_email_in_identity_belongs_to_other_user(self, verify_mock, request_post_mock,
                                                     msg_mock):
        """Test adding a stronger identity and changing the primary email."""
        UserFactory.create(email='foo@example.com')
        user1 = UserFactory.create(email='bar@example.com')

        verify_mock.return_value = json.dumps({
            'email': 'foo@example.com',
            'email_verified': True,
            'sub': 'ad|ldap'
        })
        post_json_mock = Mock()
        post_json_mock.json.return_value = {
            'id_token': 'id_token'
        }
        with self.login(user1) as client:
            session = client.session
            session['oidc_verify_nonce'] = 'nonce'
            session['oidc_verify_state'] = 'state'
            session.save()
            response = client.get(self.url, self.get_data, follow=True)
            msg = 'The email in this identity is used by another user.'
            msg_mock.error.assert_called_once_with(ANY, msg)
            with override_script_prefix('/en-US/'):
                url = reverse('phonebook:profile_edit')
            self.assertRedirects(response, url)
