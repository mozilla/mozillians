from django.contrib.auth.models import User

from funfactory.urlresolvers import reverse
from nose.tools import eq_
from pyquery import PyQuery as pq

from common.tests import ESTestCase, TestCase
from common import browserid_mock
from groups.models import Group
from users.models import UserProfile

Group.objects.get_or_create(name='staff', system=True)


class TestThingsForPeople(TestCase):
    """Verify that the wrong users don't see things."""

    def test_searchbox(self):
        url = reverse('home')
        r = self.client.get(url)
        doc = pq(r.content)
        assert not doc('input[type=text]')
        r = self.pending_client.get(url)
        doc = pq(r.content)
        assert not doc('input[type=text]')
        r = self.mozillian_client.get(url)
        doc = pq(r.content)
        assert doc('input[type=text]')

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
        url = reverse('profile', args=['pending'])
        r = self.mozillian_client.get(url)
        doc = pq(r.content)
        assert doc('#vouch-form button')
        r = self.pending_client.get(url)
        doc = pq(r.content)
        errmsg = 'Self vouching... silliness.'
        assert not doc('#vouch-form button'), errmsg
        assert 'Vouch for me' not in r.content, errmsg


class VouchTest(ESTestCase):

    def test_vouch_method(self):
        """Test UserProfile.vouch()

        Assert that a previously unvouched user shows up as unvouched in the
        database.

        Assert that when vouched they are listed as vouched.
        """
        vouchee = self.mozillian.get_profile()
        profile = self.pending.get_profile()
        assert not profile.is_vouched, 'User should not yet be vouched.'
        r = self.mozillian_client.get(reverse('search'),
                                      {'q': self.pending.email})
        assert 'Non-Vouched' in r.content, (
                'User should not appear as a Mozillian in search.')

        profile.vouch(vouchee)
        profile = UserProfile.objects.get(pk=profile.pk)
        assert profile.is_vouched, 'User should be marked as vouched.'

        r = self.mozillian_client.get(reverse('profile', args=['pending']))
        eq_(r.status_code, 200)
        doc = pq(r.content)
        assert 'Mozillian Profile' in r.content, (
                'User should appear as having a vouched profile.')
        assert not 'Pending Profile' in r.content, (
                'User should not appear as having a pending profile.')
        assert not doc('#pending-approval'), (
                'Pending profile div should not be in DOM.')

        # Make sure the user appears vouched in search results
        r = self.mozillian_client.get(reverse('search'),
                                      {'q': self.pending.email})
        assert 'Mozillian' in r.content, (
                'User should appear as a Mozillian in search.')


class TestUser(TestCase):
    """Test User functionality"""

    def test_userprofile(self):
        u = User.objects.create(username='tmp', email='tmp@domain.com')

        UserProfile.objects.all().delete()

        # Somehow the User lacks a UserProfile
        self.assertRaises(UserProfile.DoesNotExist,
                          u.get_profile)

        # Sign in
        with browserid_mock.mock_browserid(u.email):
            d = dict(assertion='qwer')
            self.client.post(reverse('browserid_verify'), d, follow=True)

        # Good to go
        assert u.get_profile()


class TestMigrateRegistration(TestCase):
        """Test funky behavior of flee ldap"""
        email = 'robot1337@domain.com'

        def test_login(self):
            """Given an invite_url go to it and redeem an invite."""
            # Lettuce make sure we have a clean slate

            info = dict(
                first_name='Akaaaaaaash',
                last_name='Desaaaaaaai',
                optin=True
            )

            self.client.logout()
            u = User.objects.create(username='robot1337', email=self.email)
            p = u.get_profile()

            u.first_name = info['first_name']
            u.last_name = ''
            u.save()
            p.save()

            # BrowserID needs an assertion not to be whiney
            d = dict(assertion='tofu')
            with browserid_mock.mock_browserid(self.email):
                r = self.client.post(reverse('browserid_verify'),
                                     d, follow=True)

            eq_(r.status_code, 200)

            # Now let's register

            with browserid_mock.mock_browserid(self.email):
                r = self.client.post(reverse('register'), info, follow=True)

            eq_(r.status_code, 200)
