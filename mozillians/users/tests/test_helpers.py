from nose.tools import eq_
from mock import patch

from mozillians.common.tests import TestCase
from mozillians.users.helpers import calculate_username
from mozillians.users.tests import UserFactory


class CalculateUsernameTests(TestCase):
    def test_base(self):
        suggested_username = calculate_username('foo@bar.com')
        eq_(suggested_username, 'foo')

    @patch('mozillians.users.helpers.USERNAME_MAX_LENGTH', 3)
    def test_extra_long_email(self):
        suggested_username = calculate_username('fooooo@bar.com')
        eq_(suggested_username, 'foo')

    def test_existing_username(self):
        UserFactory.create(username='foo')
        suggested_username = calculate_username('foo@example.com')
        eq_(suggested_username, 'foo1')

    @patch('mozillians.users.helpers.USERNAME_MAX_LENGTH', 3)
    def test_existing_username_no_alternative(self):
        UserFactory.create(username='foo')
        suggested_username = calculate_username('fooooo@bar.com')
        eq_(suggested_username, 'WMAO-pvtclchsp9LX3hk8PGRytU')
