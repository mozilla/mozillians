from django.forms import ValidationError

from nose.tools import assert_raises, eq_

from mozillians.common.tests import TestCase
from mozillians.phonebook.validators import (validate_email, validate_twitter,
                                             validate_username_not_url,
                                             validate_phone_number)


class ValidatorTests(TestCase):
    def test_twitter_username_restrictions(self):
        assert_raises(ValidationError, validate_twitter, "thisusernameiswaytoolong")
        assert_raises(ValidationError, validate_twitter, "no$character")

    def test_twitter_username_parsing(self):
        username = 'https://www.twitter.com/@validusername'
        eq_('validusername', validate_twitter(username))
        username = '@ValidName'
        eq_('ValidName', validate_twitter(username))

    def test_username_not_url_with_username(self):
        username = 'someusername'
        eq_(username, validate_username_not_url(username))

    def test_username_not_url_with_url(self):
        username = 'http://somesite.com'
        assert_raises(ValidationError, validate_username_not_url, username)

    def test_validate_email_without_email(self):
        username = 'testtest.com'
        assert_raises(ValidationError, validate_email, username)

    def test_validate_email_with_email(self):
        username = 'test@test.com'
        eq_(username, validate_email(username))

    def test_validate_phone_number_restrictions(self):
        assert_raises(ValidationError, validate_phone_number, 'notanumber')
        # Number is too short
        assert_raises(ValidationError, validate_phone_number, '+1234')
        # Number is too long
        assert_raises(ValidationError, validate_phone_number, '+12345678910111213')
        # Number is not in international format
        assert_raises(ValidationError, validate_phone_number, '123456789')

    def test_validate_phone_number_valid_input(self):
        # 5 digits
        eq_('+12345', validate_phone_number('+12345'))
        # 15 digits
        eq_('+123456789111111', validate_phone_number('+123456789111111'))
        # Somewhere in between
        eq_('+12345678910', validate_phone_number('+12345678910'))
        # With spaces please
        eq_('+12345678910', validate_phone_number('+123 4567 8910'))
        # Starting with 00
        eq_('+12345678910', validate_phone_number('00123 4567 8910'))
