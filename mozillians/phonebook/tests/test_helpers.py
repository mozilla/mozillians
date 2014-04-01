import tower
from nose.tools import eq_

from mozillians.common.tests import TestCase
from mozillians.groups.models import GroupMembership
from mozillians.groups.tests import GroupFactory
from mozillians.phonebook.helpers import langcode_to_name, search_result_context
from mozillians.users.tests import UserFactory


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


class SearchResultContextTests(TestCase):
    def test_profile(self):
        # Passing a profile puts a profile in the context
        profile = UserFactory().userprofile
        x = search_result_context({}, profile)
        eq_(x['profile'], profile)

    def test_membership(self):
        # Passing a membership puts a profile in the context
        profile = UserFactory().userprofile
        group = GroupFactory()
        membership = GroupMembership(userprofile=profile, group=group)
        x = search_result_context({}, membership)
        eq_(x['profile'], profile)
