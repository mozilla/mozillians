from django.contrib.auth.models import User

from funfactory.urlresolvers import reverse
from nose.tools import eq_
from pyquery import PyQuery as pq

from common.browserid_mock import mock_browserid
from common.tests import ESTestCase, TestCase
from groups.models import Group
from users.models import UserProfile

Group.objects.get_or_create(name='staff', system=True)


class RegistrationTest(TestCase):
    """Tests registration."""
    # Assertion doesn't matter since we monkey patched it for testing
    fake_assertion = 'mrfusionsomereallylongstring'

    def test_mozillacom_registration(self):
        """Verify @mozilla.com users are auto-vouched and marked "staff"."""

        d = dict(assertion=self.fake_assertion)
        with mock_browserid('mrfusion@mozilla.com'):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        d = dict(
                 username='ad',
                 email='mrfusion@mozilla.com',
                 first_name='Akaaaaaaash',
                 last_name='Desaaaaaaai',
                 password='tacoface',
                 confirmp='tacoface',
                 optin=True
        )
        with mock_browserid('mrfusion@mozilla.com'):
            r = self.client.post(reverse('register'), d, follow=True)

        doc = pq(r.content)

        assert r.context['user'].get_profile().is_vouched, (
                "Moz.com should be auto-vouched")

        assert not doc('#pending-approval'), (
                'Moz.com profile page should not having pending vouch div.')

        assert r.context['user'].get_profile().groups.filter(name='staff'), (
                'Moz.com should belong to the "staff" group.')

    def test_plus_signs(self):
        email = 'mrfusion+dotcom@mozilla.com'
        d = dict(assertion=self.fake_assertion)
        with mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        d = dict(
                 username='ad',
                 email=email,
                 first_name='Akaaaaaaash',
                 last_name='Desaaaaaaai',
                 password='tacoface',
                 confirmp='tacoface',
                 optin=True
        )
        with mock_browserid(email):
            self.client.post(reverse('register'), d, follow=True)

        assert User.objects.filter(email=d['email'])

    def test_username(self):
        """Test that we can submit a perfectly cromulent username.

        We verify that /:username then works as well.
        """
        email = 'mrfusion+dotcom@mozilla.com'
        d = dict(assertion=self.fake_assertion)
        with mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)
        d = dict(
                 email=email,
                 username='mrfusion',
                 first_name='Akaaaaaaash',
                 last_name='Desaaaaaaai',
                 password='tacoface',
                 confirmp='tacoface',
                 optin=True
        )
        with mock_browserid(email):
            r = self.client.post(reverse('register'), d)
        eq_(r.status_code, 302, "Problems if we didn't redirect...")
        u = User.objects.filter(email=d['email'])[0]
        eq_(u.username, 'mrfusion', "Username didn't get set.")

        r = self.mozillian_client.get(reverse('profile', args=['mrfusion']),
                                              follow=True)
        eq_(r.status_code, 200)
        eq_(r.context['profile'].user_id, u.id)

    def test_bad_username(self):
        """`about` is a terrible username, as are it's silly friends.

        Let's make some stop words *and* analyze the routing system,
        whenever someone sets their username and verify that they can't
        be "about" or "help" or anything that is in use.
        """
        email = 'mrfusion+dotcom@mozilla.com'
        badnames = ('about', 'save', 'tag', 'group', 'username', 'register',
                    'photo', 'media', 'u/foobar', 'owen@coutts')

        # BrowserID needs an assertion not to be whiney
        d = dict(assertion=self.fake_assertion)
        with mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        for name in badnames:
            d = dict(
                    email=email,
                    username=name,
                    first_name='Akaaaaaaash',
                    last_name='Desaaaaaaai',
                    optin=True
            )
            with mock_browserid(email):
                r = self.client.post(reverse('register'), d)

            eq_(r.status_code, 200,
                'This form should fail for "%s", and say so.' % name)
            assert r.context['form'].errors, (
                "Didn't raise errors for %s" % name)

    def test_repeat_username(self):
        """Verify one cannot repeat email adresses."""
        register = dict(
                 username='repeatedun',
                 first_name='Akaaaaaaash',
                 last_name='Desaaaaaaai',
                 optin=True
        )

        # Create first user
        email1 = 'mRfUsIoN@mozilla.com'
        register.update(email=email1)
        d = dict(assertion=self.fake_assertion)
        with mock_browserid(email1):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        with mock_browserid(email1):
            self.client.post(reverse('register'), register, follow=True)

        self.client.logout()
        # Create a different user
        email2 = 'coldfusion@gmail.com'
        register.update(email=email2)
        with mock_browserid(email2):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        with mock_browserid(email2):
            r = self.client.post(reverse('register'), register, follow=True)

        # Make sure we can't use the same username twice
        assert r.context['form'].errors, "Form should throw errors."


class TestThingsForPeople(TestCase):
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
