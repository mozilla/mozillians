from nose.tools import eq_
from mock import patch

from mozillians.common.tests import TestCase
from mozillians.users import AVAILABLE_LANGUAGES, get_translated_languages
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


class GetTranslatedLanguagesTests(TestCase):
    def test_invalid_locale(self):
        """Test with invalid locale, must default to english translations."""
        languages = get_translated_languages('foobar')
        english_languages = get_translated_languages('en')
        eq_(english_languages, languages)

    def test_valid_locale(self):
        get_translated_languages('en')
        self.assertIn('en', AVAILABLE_LANGUAGES.keys())

    def test_valid_locale_not_cached(self):
        # check that key does not exist
        self.assertNotIn('el', AVAILABLE_LANGUAGES.keys())
        get_translated_languages('el')
        self.assertIn('el', AVAILABLE_LANGUAGES.keys())
