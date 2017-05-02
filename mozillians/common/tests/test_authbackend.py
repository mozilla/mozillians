from django.http import HttpRequest
from django.test import override_settings

from mock import Mock, patch
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.users.models import ExternalAccount
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

    def test_add_a_new_email(self):
        """Test to add a new email in an authenticated user."""

        user = UserFactory.create(email='foo@example.com')
        request_mock = Mock(spec=HttpRequest)
        request_mock.user = user
        request_mock.user.is_authenticated = Mock()
        request_mock.user.is_authenticated.return_value = True
        self.backend.request = request_mock
        claims = {
            'email': 'bar@example.com'
        }
        email_q = ExternalAccount.objects.filter(type=ExternalAccount.TYPE_EMAIL,
                                                 user=user.userprofile,
                                                 identifier='bar@example.com')
        ok_(not email_q.exists())
        returned_user = self.backend.filter_users_by_claims(claims)
        email_q = ExternalAccount.objects.filter(type=ExternalAccount.TYPE_EMAIL,
                                                 user=user.userprofile,
                                                 identifier='bar@example.com')
        ok_(email_q.exists())
        eq_(len(returned_user), 1)
        eq_(returned_user[0], user)

    @patch('mozillians.common.authbackend.messages.error')
    def test_alternate_email_already_exists(self, mocked_message):
        """Test to add an email that already exists."""

        user = UserFactory.create(email='foo@example.com')
        ExternalAccount.objects.create(type=ExternalAccount.TYPE_EMAIL,
                                       user=user.userprofile,
                                       identifier='bar@example.com')
        request_mock = Mock(spec=HttpRequest)
        request_mock.user = user
        request_mock.user.is_authenticated = Mock()
        request_mock.user.is_authenticated.return_value = True
        self.backend.request = request_mock
        claims = {
            'email': 'bar@example.com'
        }
        returned_user = self.backend.filter_users_by_claims(claims)
        email_q = ExternalAccount.objects.filter(type=ExternalAccount.TYPE_EMAIL,
                                                 user=user.userprofile,
                                                 identifier='bar@example.com')
        ok_(email_q.exists())
        eq_(len(returned_user), 1)
        eq_(returned_user[0], user)
        ok_(not mocked_message.called)

    @patch('mozillians.common.authbackend.messages.error')
    def test_add_primary_email_as_alternate(self, mocked_message):
        """Test to add the primary email as alternate."""

        user = UserFactory.create(email='foo@example.com')
        request_mock = Mock(spec=HttpRequest)
        request_mock.user = user
        request_mock.user.is_authenticated = Mock()
        request_mock.user.is_authenticated.return_value = True
        self.backend.request = request_mock
        claims = {
            'email': 'foo@example.com'
        }
        self.backend.filter_users_by_claims(claims)
        email_q = ExternalAccount.objects.filter(type=ExternalAccount.TYPE_EMAIL,
                                                 user=user.userprofile,
                                                 identifier='foo@example.com')
        ok_(not mocked_message.called)
        ok_(not email_q.exists())

    @patch('mozillians.common.authbackend.messages.error')
    def test_add_email_belonging_to_other_user(self, mocked_message):
        """Test to add an email belonging to another user."""

        user1 = UserFactory.create(email='foo@example.com')
        UserFactory.create(email='bar@example.com')
        request_mock = Mock(spec=HttpRequest)
        request_mock.user = user1
        request_mock.user.is_authenticated = Mock()
        request_mock.user.is_authenticated.return_value = True
        self.backend.request = request_mock
        claims = {
            'email': 'bar@example.com'
        }
        returned_user = self.backend.filter_users_by_claims(claims)
        email_q = ExternalAccount.objects.filter(type=ExternalAccount.TYPE_EMAIL,
                                                 user=user1.userprofile,
                                                 identifier='bar@example.com')
        mocked_message.assert_called_once_with(request_mock, u'Email bar@example.com already '
                                                             'exists in the database.')
        ok_(not email_q.exists())
        eq_(len(returned_user), 1)
        eq_(returned_user[0], user1)
