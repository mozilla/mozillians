from django.contrib.auth.models import User

from funfactory.urlresolvers import reverse
from nose.tools import eq_
from pyquery import PyQuery as pq

from groups.models import Group
from phonebook.tests import LDAPTestCase, MOZILLIAN, PENDING


Group.objects.get_or_create(name='staff', system=True)


class TestThingsForPeople(LDAPTestCase):
    """Verify that the wrong users don't see things."""

    def test_searchbox(self):
        url = reverse('home')
        r = self.client.get(url)
        doc = pq(r.content)
        assert not doc('input[type=search]')
        r = self.pending_client.get(url)
        doc = pq(r.content)
        assert not doc('input[type=search]')
        r = self.mozillian_client.get(url)
        doc = pq(r.content)
        assert doc('input[type=search]')

    def test_invitelink(self):
        url = reverse('home')
        r = self.client.get(url)
        doc = pq(r.content)
        assert not doc('a#invite')
        r = self.pending_client.get(url)
        doc = pq(r.content)
        assert not doc('a#invite'), "Unvouched can't invite."
        r = self.mozillian_client.get(url)
        doc = pq(r.content)
        assert doc('a#invite')

    def test_register_redirects_for_authenticated_users(self):
        """Ensure only anonymous users can register an account."""
        r = self.client.get(reverse('home'))
        self.assertTrue(200 == r.status_code,
                        'Anonymous users can access the homepage to '
                        'begin registration flow')

        r = self.mozillian_client.get(reverse('register'))
        eq_(302, r.status_code,
            'Authenticated users are redirected from registration.')

    def test_vouchlink(self):
        """No vouch link when PENDING looks at PENDING."""
        url = reverse('profile', args=[PENDING['uniq_id']])
        r = self.mozillian_client.get(url)
        doc = pq(r.content)
        assert doc('#vouch-form button')
        r = self.pending_client.get(url)
        doc = pq(r.content)
        errmsg = 'Self vouching... silliness.'
        assert not doc('#vouch-form button'), errmsg
        assert 'Vouch for me' not in r.content, errmsg


def get_profile(email):
    """Get a UserProfile for a particular user."""
    return User.objects.get(email=email).get_profile()


class VouchTest(LDAPTestCase):
    def test_vouchify_task(self):
        """``vouchify`` task should mark vouched users in the db.

        Test that an already vouched user will will look right in the DB.
        Note this relies on LDAPTestCase having run ``cron.vouchify()``.
        """
        profile = get_profile(MOZILLIAN['email'])
        assert profile.is_vouched

    def test_vouch_method(self):
        """Test UserProfile.vouch()

        Assert that a previously unvouched user shows up as unvouched in the
        database.

        Assert that when vouched they are listed as vouched.
        """
        vouchee = get_profile(MOZILLIAN['email'])
        profile = get_profile(PENDING['email'])
        assert not profile.is_vouched, 'User should not yet be vouched.'
        r = self.mozillian_client.get(reverse('phonebook.search'),
                                      {'q': PENDING['email']},follow=True)


        assert 'Pending Profile' in r.content, (
                'User should not appear as a Mozillian in search.')

        profile.vouch(vouchee)
        profile = get_profile(PENDING['email'])
        assert profile.is_vouched, 'User should be marked as vouched.'

        r = self.mozillian_client.get(reverse('profile',
                                              args=[PENDING['uniq_id']]))
        doc = pq(r.content)
        assert 'Mozillian Profile' in r.content, (
                'User should appear as having a vouched profile.')
        assert not 'Pending Profile' in r.content, (
                'User should not appear as having a pending profile.')
        assert not doc('#pending-approval'), (
                'Pending profile div should not be in DOM.')

        # Make sure the user appears vouched in search results
        r = self.mozillian_client.get(reverse('phonebook.search'),
                                      {'q': PENDING['email']})
        assert not 'Pending Profile' in r.content, (
                'User should appear as a Mozillian in search.')
