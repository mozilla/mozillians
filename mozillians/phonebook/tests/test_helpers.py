import tower
from nose.tools import eq_

from mozillians.common.tests import TestCase
from mozillians.phonebook.helpers import langcode_to_name, langname_to_code, simple_urlize


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


class LanguageNameToCodeTests(TestCase):

    def test_valid_name(self):
        """Test language code with a valid name."""
        code = langname_to_code('russian')
        eq_(code, 'ru')

    def test_invalid_name(self):
        """Test language code with invalid name."""
        code = langname_to_code('barfoo')
        eq_(code, None)


class SimpleUrlizeTests(TestCase):

    def test_valid_http_url(self):
        """Test that a given string is a valid http url"""
        test_url = 'http://www.test.com'
        urlized_url = simple_urlize(test_url)
        eq_(urlized_url, '<a href="%s">%s</a>' % (test_url, test_url))

    def test_invalid_http_url(self):
        """Test that a given string is an invalid http url"""
        test_url = 'http://test'
        urlized_url = simple_urlize(test_url)
        eq_(urlized_url, test_url)

    def test_valid_https_url(self):
        """Test that a given string is a valid https url"""
        test_url = 'https://www.test.com'
        urlized_url = simple_urlize(test_url)
        eq_(urlized_url, '<a href="%s">%s</a>' % (test_url, test_url))

    def test_invalid_https_url(self):
        """Test that a given string is an invalid https url"""
        test_url = 'https://test'
        urlized_url = simple_urlize(test_url)
        eq_(urlized_url, test_url)

    def test_invalid_string_url(self):
        """Test that a given string is an invalid url"""
        test_url = 'test'
        urlized_url = simple_urlize(test_url)
        eq_(urlized_url, test_url)
