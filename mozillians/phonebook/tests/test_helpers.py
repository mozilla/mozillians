import tower
from nose.tools import eq_

from mozillians.common.tests import TestCase
from mozillians.phonebook.helpers import langcode_to_name


class LanguageCodeToNameTests(TestCase):

    def test_valid_code(self):
        """Test the name of a language with valid language code."""
        tower.activate('fr')
        name = langcode_to_name('en')
        eq_(name, u'Anglais')

    def test_invalid_code(self):
        """Test the language name with invalid language code."""
        tower.activate('fr')
        name = langcode_to_name('foobar')
        eq_(name, 'foobar')
