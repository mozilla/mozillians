import json

from funfactory.urlresolvers import reverse
from nose.tools import eq_
from pyquery import PyQuery as pq

from phonebook.tests import LDAPTestCase, MOZILLIAN, PENDING, mozillian_client
from groups.helpers import stringify_groups
from groups.models import Group
from users.tests import get_profile


NORMAL_GROUP = Group.objects.create(name='cheesezilla')
HIDDEN_GROUP = Group.objects.create(name=':ghost')


class GroupTest(LDAPTestCase):
    """Test the group/grouping system."""

    def test_default_groups(self):
        """Ensure the user has the proper amount of groups upon creation."""
        assert not get_profile(MOZILLIAN['email']).groups.all(), (
                'User should have no groups by default.')

    def test_pending_user_cant_edit_groups(self):
        """Ensure pending users can't add/edit groups."""
        profile = get_profile(PENDING['email'])
        assert not profile.groups.all(), 'User should have no groups.'

        client = mozillian_client(PENDING['email'])
        client.post(reverse('phonebook.edit_profile'),
                    dict(last_name='McAwesomepants', groups='Awesome foo Bar'),
                    follow=True)

        assert not profile.groups.all(), (
                "Pending user shouldn't be able to edit groups.")

    def test_string_split_works_properly(self):
        """Ensure groups are saved correctly from a space-delimited string."""
        profile = get_profile(MOZILLIAN['email'])
        profile.groups.clear()
        assert not profile.groups.all(), (
                'User has no groups at beginning of test.')

        client = mozillian_client(MOZILLIAN['email'])
        client.post(reverse('phonebook.edit_profile'),
                    dict(
                         last_name='McAwesomepants',
                         # This should result in four groups
                         groups='Awesome   foo  Bar     g     '),
                    follow=True)

        eq_(4, profile.groups.count(), 'User should have four groups.')

    def test_system_attribute_is_denormalized(self):
        """Ensure the pre_save signal to mark groups as "system" works."""
        # We shouldn't even explicitly set system as True, but we can
        # make sure it gets set to false as this group doesn't look like
        # a system group -- this is useful if we rename groups (say, want
        # to open them up and remove their "system-ness").
        group = Group.objects.create(name='vagabond-hippie', system=True)
        assert not group.system, 'Group should not be a system group.'

        system_group = Group.objects.create(name='vagabond:hippie')
        assert system_group.system, 'The system attribute should be True.'

    def test_groups_are_always_lowercase(self):
        """Ensure all groups are saved with lowercase names only."""
        Group.objects.create(name='lowercase')
        Group.objects.create(name='Uppercase')
        Group.objects.create(name='YELLING')

        # Make sure groups created from a profile are lowercase too.
        profile = get_profile(MOZILLIAN['email'])
        profile.groups.create(name='ILIKEITLOUD')

        for g in Group.objects.all():
            assert g.name == g.name.lower(), 'All groups should be lowercase.'

    def test_groups_are_case_insensitive(self):
        """Ensure groups are case insensitive."""
        profile = get_profile(MOZILLIAN['email'])

        client = mozillian_client(MOZILLIAN['email'])
        client.post(reverse('phonebook.edit_profile'),
                    dict(
                         last_name='tofumatt',
                         groups='Awesome foo Bar'),
                    follow=True)

        eq_(3, profile.groups.count(), 'Three groups should be saved.')

        group_string = stringify_groups(profile.groups.all())

        for g in ['awesome', 'bar', 'foo']:
            assert g in group_string, (
                    'All three saved groups should be lowercase.')
        assert not 'Awesome' in group_string, (
                'Uppercase group should be transformed to lowercase.')

        # Make an AJAX request for a group using a capital letter.
        r = client.get(reverse('group_search'), dict(term='Awesome'),
                       HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        for g in json.loads(r.content):
            assert g.name == g.name.lower(), (
                    'Group search is case-insensitive.')

    def test_user_cant_create_system_groups(self):
        """Make sure users can't create system groups/add them to a profile."""
        profile = get_profile(MOZILLIAN['email'])

        client = mozillian_client(MOZILLIAN['email'])
        client.post(reverse('phonebook.edit_profile'),
                    dict(
                         last_name='tofumatt',
                         groups='mozilla:festival good stuff'),
                    follow=True)

        groups = profile.groups.all()

        eq_(2, len(groups), 'Only two groups should have been added.')

        for g in groups:
            assert not g.system, (
                    "None of this user's groups should be system groups.")

    def test_users_cant_remove_system_groups(self):
        """Make sure removing groups in a profile doesn't delete system groups.

        When a user deletes their (visible) groups in the edit profile page,
        they shouldn't delete any system groups.
        """
        profile = get_profile(MOZILLIAN['email'])

        profile.groups.add(NORMAL_GROUP, HIDDEN_GROUP)
        eq_(2, profile.groups.count(), 'User should have both groups.')

        # Edit this user's profile and remove a group.
        client = mozillian_client(MOZILLIAN['email'])
        response = client.post(reverse('phonebook.edit_profile'),
                               dict(last_name="McLovin'", groups=''),
                               follow=True)
        doc = pq(response.content)
        assert not doc('#id_groups').attr('value'), (
                'User should have no visible groups.')

        assert profile.groups.count(), 'User should not have zero groups.'
        for g in profile.groups.all():
            assert g.system, 'User should only have system groups.'

    def test_users_cant_see_system_groups(self):
        """Make sure system groups don't show up in responses."""
        profile = get_profile(MOZILLIAN['email'])

        profile.groups.add(NORMAL_GROUP, HIDDEN_GROUP)
        eq_(2, profile.groups.count(), 'User should have both groups.')

        client = mozillian_client(MOZILLIAN['email'])

        # Edit the user's profile to check for hidden groups there.
        response = client.get(reverse('phonebook.edit_profile'))
        doc = pq(response.content)
        assert NORMAL_GROUP.name in doc('#id_groups').attr('value'), (
                'Group "%s" should be visible.' % NORMAL_GROUP.name)
        assert not HIDDEN_GROUP.name in doc('#id_groups').attr('value'), (
                'Group "%s" should hidden.' % HIDDEN_GROUP.name)
