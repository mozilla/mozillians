# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from django.conf import settings
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase

from mock import ANY, Mock, patch

from django_browserid.auth import BrowserIDBackend, default_username_algo, verify
from django_browserid.tests import mock_browserid

try:
    from django.contrib.auth import get_user_model
    from django_browserid.tests.models import CustomUser
except ImportError:
    get_user_model = False


def new_user(email, username=None):
        """Creates a user with the specified email for testing."""
        if username is None:
            username = default_username_algo(email)
        return User.objects.create_user(username, email)


class BrowserIDBackendTests(TestCase):
    def auth(self, verified_email=None, browserid_extra=None):
        """
        Attempt to authenticate a user with BrowserIDBackend.

        If verified_email is None, verification will fail, otherwise it will
        pass and return the specified email.
        """
        with mock_browserid(verified_email):
            backend = BrowserIDBackend()
            return backend.authenticate(assertion='asdf', audience='asdf', browserid_extra=browserid_extra)

    def test_failed_verification(self):
        # If verification fails, return None.
        self.assertTrue(self.auth(None) is None)

    def test_duplicate_emails(self):
        # If there are two users with the same email address, return None.
        new_user('a@example.com', 'test1')
        new_user('a@example.com', 'test2')
        self.assertTrue(self.auth('a@example.com') is None)

    def test_auth_success(self):
        # If a single user is found with the verified email, return an instance
        # of their user object.
        user = new_user('a@example.com')
        self.assertEqual(self.auth('a@example.com'), user)

    @patch.object(settings, 'BROWSERID_CREATE_USER', False)
    def test_no_create_user(self):
        # If user creation is disabled and no user is found, return None.
        self.assertTrue(self.auth('a@example.com') is None)

    @patch.object(settings, 'BROWSERID_CREATE_USER', True)
    def test_create_user(self):
        # If user creation is enabled and no user is found, return a new
        # User.
        user = self.auth('a@example.com')
        self.assertTrue(user is not None)
        self.assertTrue(isinstance(user, User))
        self.assertEqual(user.email, 'a@example.com')

    @patch.object(settings, 'BROWSERID_CREATE_USER',
                  'django_browserid.tests.test_auth.new_user')
    @patch('django_browserid.tests.test_auth.new_user')
    def test_custom_create_user(self, create_user):
        # If user creation is enabled with a custom create function and no user
        # is found, return the new user created with the custom function.
        create_user.return_value = 'test'
        self.assertEqual(self.auth('a@example.com'), 'test')
        create_user.assert_called_with('a@example.com')

    @patch.object(settings, 'BROWSERID_USERNAME_ALGO')
    @patch.object(settings, 'BROWSERID_CREATE_USER', True)
    def test_custom_username_algorithm(self, username_algo):
        # If a custom username algorithm is specified, use it!
        username_algo.return_value = 'test'
        user = self.auth('a@b.com')
        self.assertEqual(user.username, 'test')

    @patch('django_browserid.auth.user_created')
    @patch.object(settings, 'BROWSERID_CREATE_USER', True)
    def test_user_created_signal(self, user_created):
        # Test that the user_created signal is called when a new user is
        # created.
        user = self.auth('a@b.com')
        user_created.send.assert_called_with(ANY, user=user)

    @patch('django_browserid.auth.verify', wraps=verify)
    def test_verify_called_with_browserid_extra(self, user_verify):
        dic = {'a': 'AlphaA'}
        self.auth('a@b.com', browserid_extra=dic)
        user_verify.assert_called_with('asdf', 'asdf', extra_params=dic)

    def test_get_user(self):
        # If a user is retrieved by the BrowserIDBackend, it should have
        # 'django_browserid.auth.BrowserIDBackend' for the backend attribute.
        user = new_user('a@example.com')
        backend = BrowserIDBackend()
        self.assertEqual(backend.get_user(user.id).backend,
                         'django_browserid.auth.BrowserIDBackend')

    def test_overriding_valid_email(self):
        class PickyBackend(BrowserIDBackend):
            def is_valid_email(self, email):
                return email != 'a@example.com'

        new_user('a@example.com', 'test1')
        new_user('b@example.com', 'test2')

        with mock_browserid('a@example.com'):
            backend = PickyBackend()
            result = backend.authenticate(assertion='asdf', audience='asdf')
            self.assertTrue(not result)

        with mock_browserid('b@example.com'):
            backend = PickyBackend()
            result = backend.authenticate(assertion='asdf', audience='asdf')
            self.assertTrue(result)

    @patch('django_browserid.auth.logger')
    def test_create_user_integrity_error(self, logger):
        # If an IntegrityError is raised during user creation, attempt to re-fetch the user in case
        # the user was created since we checked for the existing account.
        backend = BrowserIDBackend()
        backend.User = Mock()
        error = IntegrityError()
        backend.User.objects.create_user.side_effect = error
        backend.User.objects.get.return_value = 'asdf'

        self.assertEqual(backend.create_user('a@example.com'), 'asdf')

        # If get raises a DoesNotExist exception, re-raise the original exception.
        backend.User.DoesNotExist = Exception
        backend.User.objects.get.side_effect = backend.User.DoesNotExist
        with self.assertRaises(IntegrityError) as e:
            backend.create_user('a@example.com')
        self.assertEqual(e.exception, error)


if get_user_model:
    # Only run custom user model tests if we're using a version of Django that
    # supports it.
    @patch.object(settings, 'AUTH_USER_MODEL', 'tests.CustomUser')
    class CustomUserModelTests(TestCase):
        def _auth(self, backend=None, verified_email=None):
            if backend is None:
                backend = BrowserIDBackend()

            with mock_browserid(verified_email):
                return backend.authenticate(assertion='asdf', audience='asdf')

        def test_existing_user(self):
            """If a custom user exists with the given email, return them."""
            user = CustomUser.objects.create(email='a@test.com')
            authed_user = self._auth(verified_email='a@test.com')
            self.assertEqual(user, authed_user)

        @patch.object(settings, 'BROWSERID_CREATE_USER', True)
        def test_create_new_user(self):
            """
            If a custom user does not exist with the given email, create a new
            user and return them.
            """
            class CustomUserBrowserIDBackend(BrowserIDBackend):
                def create_user(self, email):
                    return CustomUser.objects.create(email=email)
            user = self._auth(backend=CustomUserBrowserIDBackend(),
                              verified_email='b@test.com')
            self.assertTrue(isinstance(user, CustomUser))
            self.assertEqual(user.email, 'b@test.com')
