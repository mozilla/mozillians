import json

from funfactory.urlresolvers import reverse
from nose.tools import eq_
from pyquery import PyQuery as pq

from phonebook.tests import LDAPTestCase, MOZILLIAN, PENDING, mozillian_client
from tags.helpers import stringify_tags
from tags.models import Tag
from users.tests import get_profile


NORMAL_TAG = Tag.objects.create(name='cheesezilla')
HIDDEN_TAG = Tag.objects.create(name=':ghost')


class TagTest(LDAPTestCase):
    """Test the tag/grouping system."""

    def test_default_tags(self):
        """Ensure the user has the proper amount of tags upon creation."""
        assert not get_profile(MOZILLIAN['email']).tags.all(), (
                'User should have no tags by default.')

    def test_pending_user_cant_edit_tags(self):
        """Ensure pending users can't add/edit tags."""
        profile = get_profile(PENDING['email'])
        assert not profile.tags.all(), 'User should have no tags.'

        client = mozillian_client(PENDING['email'])
        client.post(reverse('phonebook.edit_profile'),
                    dict(
                         last_name='McAwesomepants',
                         tags='Awesome foo Bar'),
                    follow=True)

        assert not profile.tags.all(), (
                "Pending user shouldn't be able to edit tags.")

    def test_string_split_works_properly(self):
        """Ensure tags sent as a space-delimited string are parsed alright."""
        profile = get_profile(MOZILLIAN['email'])
        profile.tags.clear()
        assert not profile.tags.all(), 'User has no tags at beginning of test.'

        client = mozillian_client(MOZILLIAN['email'])
        client.post(reverse('phonebook.edit_profile'),
                    dict(
                         last_name='McAwesomepants',
                         # This should result in four tags
                         tags='Awesome   foo  Bar     g     '),
                    follow=True)

        eq_(4, len(profile.tags.all()), 'User should have four tags.')

    def test_system_attribute_is_denormalized(self):
        """Ensure the pre_save signal to mark tags as "system" works."""
        # We shouldn't even explicitly set system as True, but we can
        # make sure it gets set to false as this tag doesn't look like
        # a system tag -- this is useful if we rename tags (say, want
        # to open them up and remove their "system-ness").
        regular_tag = Tag.objects.create(name='vagabond-hippie', system=True)
        assert not regular_tag.system, 'Tag should not be a system tag.'

        system_tag = Tag.objects.create(name='vagabond:hippie')
        assert system_tag.system, 'The system attribute should be True.'

    def test_tags_are_always_lowercase(self):
        """Ensure all tags are saved with lowercase names only."""
        Tag.objects.create(name='lowercase')
        Tag.objects.create(name='Uppercase')
        Tag.objects.create(name='YELLING')

        # Make sure tags created from a profile are lowercase too.
        profile = get_profile(MOZILLIAN['email'])
        profile.tags.create(name='ILIKEITLOUD')

        for t in Tag.objects.all():
            assert t.name == t.name.lower(), 'All tags are lowercase.'

    def test_tags_are_case_insensitive(self):
        """Ensure tags are case insensitive/respect the original tag's case."""
        profile = get_profile(MOZILLIAN['email'])

        client = mozillian_client(MOZILLIAN['email'])
        client.post(reverse('phonebook.edit_profile'),
                    dict(
                         last_name='tofumatt',
                         tags='Awesome foo Bar'),
                    follow=True)

        eq_(3, len(profile.tags.all()), 'Three tags should be saved.')

        tag_string = stringify_tags(profile.tags.all())

        for t in ['awesome', 'bar', 'foo']:
            assert t in tag_string, 'All three saved tags should be lowercase.'
        assert not 'Awesome' in tag_string, (
                'Uppercase tag should be transformed to lowercase.')

        # Make an AJAX request for a tag using a capital letter.
        r = client.get(reverse('tag_search'), dict(term='Awesome'),
                       HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        for t in json.loads(r.content):
            assert t.name == t.name.lower(), 'Tag search is case-insensitive.'

    def test_users_cant_remove_system_tags(self):
        """Make sure removing tags in a profile doesn't delete system tags.

        When a user deletes their (visible) tags in the edit profile page,
        they shouldn't delete any system tags.
        """
        profile = get_profile(MOZILLIAN['email'])

        profile.tags.add(NORMAL_TAG, HIDDEN_TAG)
        eq_(2, len(profile.tags.all()), 'User should have both tags.')

        # Edit this user's profile and remove a tag.
        client = mozillian_client(MOZILLIAN['email'])
        response = client.post(reverse('phonebook.edit_profile'),
                               dict(tags=''), follow=True)
        doc = pq(response.content)
        assert not doc('#id_tags').attr('value'), (
                'User should have no visible tags.')
        eq_(HIDDEN_TAG, profile.tags.get(name=HIDDEN_TAG.name),
            'User should still has the system tag.')

    def test_users_cant_see_system_tags(self):
        """Make sure system tags don't show up in responses."""
        profile = get_profile(MOZILLIAN['email'])

        profile.tags.add(NORMAL_TAG, HIDDEN_TAG)
        eq_(2, len(profile.tags.all()), 'User should have both tags.')

        client = mozillian_client(MOZILLIAN['email'])

        # Edit the user's profile to check for hidden tags there.
        response = client.get(reverse('phonebook.edit_profile'))
        doc = pq(response.content)
        assert NORMAL_TAG.name in doc('#id_tags').attr('value'), (
                'Tag "%s" should be visible.' % NORMAL_TAG.name)
        assert not HIDDEN_TAG.name in doc('#id_tags').attr('value'), (
                'Tag "%s" should hidden.' % HIDDEN_TAG.name)
