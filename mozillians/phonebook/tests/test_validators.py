from django.forms import ValidationError

from nose.tools import assert_raises, eq_

from mozillians.common.tests import TestCase
from mozillians.phonebook.validators import (validate_email, validate_twitter,
                                             validate_username_not_url)


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
