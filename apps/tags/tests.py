from django.contrib.auth.models import User

from funfactory.urlresolvers import reverse
from nose.tools import eq_
from pyquery import PyQuery as pq

from phonebook.tests import LDAPTestCase, MOZILLIAN, mozillian_client
from tags.models import Tag


class TagTest(LDAPTestCase):
    """Test the tag/grouping system."""

    def test_default_tags(self):
        """Verify that a UserProfile can have tags."""
        user = User.objects.get(email=MOZILLIAN['email'])
        profile = user.get_profile()
        eq_(0, len(profile.tags.all()), 'User has no tags by default.')

    def test_mozillian_can_have_tags(self):
        """Allow a mozillian to have zero, one, or many tags."""
        user = User.objects.get(email=MOZILLIAN['email'])
        profile = user.get_profile()
        eq_(0, len(profile.tags.all()), 'User can have no tags.')

        normal_tag = Tag(name='Cool cat')
        normal_tag.save()
        another_tag = Tag(name='Ruff rider')
        another_tag.save()

        profile.tags.add(normal_tag)
        profile.save()
        eq_(1, len(profile.tags.all()), 'User can have a single tag.')

        profile.tags.add(another_tag)
        profile.save()
        eq_(2, len(profile.tags.all()), 'User can have many tags.')

    def test_users_cant_remove_hidden_tags(self):
        """Make sure removing tags in a profile doesn't delete hidden tags.

        When a user deletes their (visible) tags in the edit profile page,
        they shouldn't delete any special "hidden" tags.
        """
        user = User.objects.get(email=MOZILLIAN['email'])
        profile = user.get_profile()
        eq_(0, len(profile.tags.all()), 'User can have no tags.')

        normal_tag = Tag(name='Regulartag')
        normal_tag.save()
        hidden_tag = Tag(name='Hiddentag', hidden=True)
        hidden_tag.save()

        profile.tags.add(normal_tag, hidden_tag)
        profile.save()
        eq_(2, len(profile.tags.all()), 'User has both tags.')

        # Edit this user's profile and remove a tag.
        client = mozillian_client(MOZILLIAN['email'])
        response = client.post(reverse('phonebook.edit_profile'),
                               dict(tags=''), follow=True)
        doc = pq(response.content)
        eq_(None, doc('#id_tags').attr('value'))
        eq_(1, len(profile.tags.filter(name='Hiddentag')),
            'User still has the hidden tag.')

    def test_users_cant_see_hidden_tags(self):
        """Make sure special/hidden tags don't show up in responses."""
        user = User.objects.get(email=MOZILLIAN['email'])
        profile = user.get_profile()
        eq_(0, len(profile.tags.all()), 'User can have no tags.')

        normal_tag = Tag(name='Regulartag')
        normal_tag.save()
        hidden_tag = Tag(name='Hiddentag', hidden=True)
        hidden_tag.save()

        profile.tags.add(normal_tag, hidden_tag)
        profile.save()
        eq_(2, len(profile.tags.all()), 'User has both tags.')

        client = mozillian_client(MOZILLIAN['email'])

        # Edit the user's profile to check for hidden tags there.
        response = client.get(reverse('phonebook.edit_profile'))
        doc = pq(response.content)
        assert 'Regulartag' in doc('#id_tags').attr('value')
        assert not 'Hiddentag' in doc('#id_tags').attr('value')

    def test_pending_user_cant_add_tags(self):
        """Ensure pending users can't add tags."""
        pass
