from nose.tools import eq_

from mozillians.common.tests import TestCase
from mozillians.phonebook.helpers import langcode_to_name


class LanguageCodeToNameTests(TestCase):

    def test_valid_code(self):
        """Test the name of a language with valid language code."""
        name = langcode_to_name('en', 'fr')
        eq_(name, 'Anglais')

    def test_invalid_code(self):
        """Test the language name with invalid language code."""
        name = langcode_to_name('foobar', 'fr')
        eq_(name, 'foobar')
