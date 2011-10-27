from funfactory.urlresolvers import reverse
from nose.tools import eq_
from pyquery import PyQuery as pq

from phonebook.tests import LDAPTestCase, MOZILLIAN, PENDING, mozillian_client
from tags.models import Tag
from users.tests import get_profile


class TagTest(LDAPTestCase):
    """Test the tag/grouping system."""

    def setUp(self):
        """Create some tags to use during testing."""
        super(TagTest, self).setUp()

        self.normal_tag = Tag(name='cheesezilla')
        self.normal_tag.save()
        self.another_tag = Tag(name='ruffrider')
        self.another_tag.save()
        self.hidden_tag = Tag(name='ghost', hidden=True)
        self.hidden_tag.save()

    def test_default_tags(self):
        """Ensure the user has the proper amount of tags upon creation."""
        eq_(0, len(get_profile(MOZILLIAN['email']).tags.all()),
            'User has no tags by default.')

    def test_mozillian_can_have_tags(self):
        """Allow a mozillian to have zero, one, or many tags."""
        profile = get_profile(MOZILLIAN['email'])
        eq_(0, len(profile.tags.all()), 'User can have no tags.')

        profile.tags.add(self.normal_tag)
        eq_(1, len(profile.tags.all()), 'User can have a single tag.')

        profile.tags.add(self.another_tag)
        eq_(2, len(profile.tags.all()), 'User can have many tags.')

    def test_users_cant_remove_hidden_tags(self):
        """Make sure removing tags in a profile doesn't delete hidden tags.

        When a user deletes their (visible) tags in the edit profile page,
        they shouldn't delete any special "hidden" tags.
        """
        profile = get_profile(MOZILLIAN['email'])
        eq_(0, len(profile.tags.all()), 'User should have no tags.')

        profile.tags.add(self.normal_tag, self.hidden_tag)
        eq_(2, len(profile.tags.all()), 'User has both tags.')

        # Edit this user's profile and remove a tag.
        client = mozillian_client(MOZILLIAN['email'])
        response = client.post(reverse('phonebook.edit_profile'),
                               dict(tags=''), follow=True)
        doc = pq(response.content)
        eq_(None, doc('#id_tags').attr('value'))
        eq_(1, len(profile.tags.filter(name=self.hidden_tag.name)),
            'User still has the hidden tag.')

    def test_users_cant_see_hidden_tags(self):
        """Make sure special/hidden tags don't show up in responses."""
        profile = get_profile(MOZILLIAN['email'])
        eq_(0, len(profile.tags.all()), 'User should have no tags.')

        profile.tags.add(self.normal_tag, self.hidden_tag)
        eq_(2, len(profile.tags.all()), 'User has both tags.')

        client = mozillian_client(MOZILLIAN['email'])

        # Edit the user's profile to check for hidden tags there.
        response = client.get(reverse('phonebook.edit_profile'))
        doc = pq(response.content)
        assert self.normal_tag.name in doc('#id_tags').attr('value'), (
               'Tag is visible.')
        assert not 'Hiddentag' in doc('#id_tags').attr('value'), (
                   'Tag is hidden.')

    def test_pending_user_cant_edit_tags(self):
        """Ensure pending users can't add/edit tags."""
        profile = get_profile(PENDING['email'])
        eq_(0, len(profile.tags.all()), 'User should have no tags.')

        client = mozillian_client(PENDING['email'])
        client.post(reverse('phonebook.edit_profile'),
                    dict(
                         last_name='McAwesomepants',
                         tags='Awesome foo Bar'),
                    follow=True)

        eq_(0, len(profile.tags.all()), 'Pending user could not edit tags.')

    def test_tags_are_case_insensitive(self):
        """Ensure tags are case insensitive/respect the original tag's case."""
        profile = get_profile(MOZILLIAN['email'])
        eq_(0, len(profile.tags.all()), 'User should have no tags.')

        client = mozillian_client(MOZILLIAN['email'])
        client.post(reverse('phonebook.edit_profile'),
                    dict(
                         last_name='tofumatt',
                         tags='Awesome foo Bar'),
                    follow=True)

        eq_(3, len(profile.tags.all()), 'Three tags were saved.')
        assert 'awesome' in profile.tags_as_string(), 'All tags are lowercase.'
        assert 'bar' in profile.tags_as_string(), 'All tags are lowercase.'
        assert 'foo' in profile.tags_as_string(), 'All tags are lowercase.'
        assert not 'Awesome' in profile.tags_as_string(), (
                   'Uppercase tag is transformed.')
