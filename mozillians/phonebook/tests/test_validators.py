from django.forms import ValidationError

from nose.tools import assert_raises, eq_

from mozillians.common.tests import TestCase
from mozillians.phonebook.validators import validate_twitter


class ValidatorTests(TestCase):
    def test_twitter_username_restrictions(self):
        assert_raises(ValidationError, validate_twitter, "thisusernameiswaytoolong")
        assert_raises(ValidationError, validate_twitter, "no$character")

    def test_twitter_username_parsing(self):
        username = 'https://www.twitter.com/@validusername'
        eq_('validusername', validate_twitter(username))
        username = '@ValidName'
        eq_('ValidName', validate_twitter(username))
