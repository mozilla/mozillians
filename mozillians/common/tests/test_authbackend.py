from django.http import HttpRequest
from django.test import override_settings

from mock import Mock, patch
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.users.models import IdpProfile
from mozillians.users.tests import UserFactory


class MozilliansAuthBackendTests(TestCase):
    """Test Mozillian's Authentication Backend."""

    @override_settings(OIDC_OP_TOKEN_ENDPOINT='https://server.example.com/token')
    @override_settings(OIDC_OP_USER_ENDPOINT='https://server.example.com/user')
    @override_settings(OIDC_RP_CLIENT_ID='example_id')
    @override_settings(OIDC_RP_CLIENT_SECRET='client_secret')
    def setUp(self):
        """Setup class."""

        # Avoid circular dependencies
        from mozillians.common.authbackend import MozilliansAuthBackend
        self.backend = MozilliansAuthBackend()

    @patch('mozillians.common.authbackend.messages')
    def test_add_a_new_email_identity(self, mocked_message):
        """Test to add a new email in an authenticated user."""
        user = UserFactory.create(email='foo@example.com')
        IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='email|',
            email=user.email,
            primary=True
        )
        claims = {
            'email': 'bar@example.com',
            'user_id': 'ad|ldap'
        }

        request_mock = Mock(spec=HttpRequest)
        request_mock.user = user
        self.backend.claims = claims
        self.backend.request = request_mock

        email_q = IdpProfile.objects.filter(profile=user.userprofile,
                                            email='bar@example.com')
        ok_(not email_q.exists())
        returned_user = self.backend.check_authentication_method(user)
        email_q = IdpProfile.objects.filter(profile=user.userprofile,
                                            email='bar@example.com')
        ok_(email_q.exists())
        eq_(returned_user, user)
        ok_(not mocked_message.called)

    @patch('mozillians.common.authbackend.messages')
    def test_identity_already_exists(self, mocked_message):
        """Test to add an email that already exists."""

        user = UserFactory.create(email='foo@example.com')
        IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='email|',
            email=user.email,
            primary=True
        )
        claims = {
            'email': 'foo@example.com',
            'user_id': 'email|'
        }

        request_mock = Mock(spec=HttpRequest)
        request_mock.user = user
        self.backend.claims = claims
        self.backend.request = request_mock
        self.backend.check_authentication_method(user)
        idp_q = IdpProfile.objects.filter(auth0_user_id='email|',
                                          email=user.email,
                                          profile=user.userprofile)
        eq_(idp_q.count(), 1)
        ok_(not mocked_message.called)

    @patch('mozillians.common.authbackend.messages')
    def test_add_idp_wrong_flow(self, mocked_message):
        """Test logging in with a weaker provider compared to the current one"""

        user = UserFactory.create(email='foo@example.com')
        IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='ad|foobar',
            primary=True
        )
        claims = {
            'email': 'bar@example.com',
            'user_id': 'foobar'
        }

        request_mock = Mock(spec=HttpRequest)
        request_mock.user = user
        self.backend.claims = claims
        self.backend.request = request_mock

        returned_user = self.backend.check_authentication_method(user)
        msg = 'Please use one of the following authentication methods: LDAP Provider'
        mocked_message.error.assert_called_once_with(request_mock, msg)

        eq_(returned_user, None)
