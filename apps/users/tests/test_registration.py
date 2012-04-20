from copy import copy

from django.contrib.auth.models import User
from django.conf import settings

from funfactory.urlresolvers import reverse
from nose.tools import eq_
from pyquery import PyQuery as pq

from common import browserid_mock
from common.tests import TestCase


class RegistrationTest(TestCase):
    # Assertion doesn't matter since we monkey patched it for testing
    fake_assertion = 'mrfusionsomereallylongstring'

    def test_mozillacom_registration(self):
        """Verify @mozilla.com users are auto-vouched and marked "staff"."""

        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid('mrfusion@mozilla.com'):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        d = dict(
                 username='ad',
                 email='mrfusion@mozilla.com',
                 first_name='Akaaaaaaash',
                 last_name='Desaaaaaaai',
                 optin=True
        )
        with browserid_mock.mock_browserid('mrfusion@mozilla.com'):
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
        with browserid_mock.mock_browserid(email):
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
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('register'), d, follow=True)

        assert User.objects.filter(email=d['email'])

    def test_username(self):
        """Test that we can submit a perfectly cromulent username.

        We verify that /:username then works as well.
        """
        email = 'mrfusion+dotcom@mozilla.com'
        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid(email):
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
        with browserid_mock.mock_browserid(email):
            r = self.client.post(reverse('register'), d)
        eq_(r.status_code, 302, "Problems if we didn't redirect...")
        u = User.objects.filter(email=d['email'])[0]
        eq_(u.username, 'mrfusion', "Username didn't get set.")

        r = self.mozillian_client.get(reverse('profile', args=['mrfusion']),
                                              follow=True)
        eq_(r.status_code, 200)
        eq_(r.context['profile_info']['username'], u.username)

    def test_username_characters(self):
        """Verify usernames can have digits/symbols, but nothing too insane."""
        email = 'mrfusion+dotcom@mozilla.com'
        username = 'mr.fu+s_i-on@246'
        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        d = dict(
                 email=email,
                 username=username,
                 first_name='Akaaaaaaash',
                 last_name='Desaaaaaaai',
                 password='tacoface',
                 confirmp='tacoface',
                 optin=True
        )
        with browserid_mock.mock_browserid(email):
            r = self.client.post(reverse('register'), d)
        eq_(r.status_code, 302, (
                'Registration flow should finish with a redirect.'))
        u = User.objects.get(email=d['email'])
        eq_(u.username, username, 'Username should be set to "%s".' % username)

        r = self.mozillian_client.get(reverse('profile', args=[username]),
                                              follow=True)
        eq_(r.status_code, 200)
        eq_(r.context['profile_info']['username'], u.username)

        # Now test a username with even weirder characters that we don't allow.
        bad_user_email = 'mrfusion+coolbeans@mozilla.com'
        bad_username = 'mr.we*rd'
        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        d = dict(
                 email=bad_user_email,
                 username=bad_username,
                 first_name='Akaaaaaaash',
                 last_name='Desaaaaaaai',
                 password='tacoface',
                 confirmp='tacoface',
                 optin=True
        )
        with browserid_mock.mock_browserid(email):
            r = self.client.post(reverse('register'), d)
        eq_(r.status_code, 302, (
                'Registration flow should fail; username is bad.'))
        assert not User.objects.filter(email=d['email']), (
                "User shouldn't exist; username was bad.")

    def test_bad_username(self):
        """`about` is a terrible username, as are its silly friends.

        Let's make some stop words *and* analyze the routing system,
        whenever someone sets their username and verify that they can't
        be "about" or "help" or anything that is in use.
        """
        email = 'mrfusion+dotcom@mozilla.com'
        badnames = getattr(settings, 'USERNAME_BLACKLIST')

        # BrowserID needs an assertion not to be whiney
        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        for name in badnames:
            d = dict(
                    email=email,
                    username=name,
                    first_name='Akaaaaaaash',
                    last_name='Desaaaaaaai',
                    optin=True
            )
            with browserid_mock.mock_browserid(email):
                r = self.client.post(reverse('register'), d)

            eq_(r.status_code, 200,
                'This form should fail for "%s", and say so.' % name)
            assert r.context['form'].errors, (
                "Didn't raise errors for %s" % name)

    def test_nickname_changes_before_vouch(self):
        """Notify pre-vouched users of URL change from nickname changes.

        See: https://bugzilla.mozilla.org/show_bug.cgi?id=736556"""
        d = dict(assertion=self.fake_assertion)
        email = 'soy@latte.net'
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        # Note: No username supplied.
        d = dict(
                 copy(self.privacy_dict),
                 email=email,
                 first_name='Tofu',
                 last_name='Matt',
                 optin=True
        )
        with browserid_mock.mock_browserid(email):
            r = self.client.post(reverse('register'), d, follow=True)

        assert r.context['user'].id, 'User should be created'
        assert not r.context['user'].get_profile().is_vouched, (
                'User should not be vouched')

        d['username'] = 'testatron'
        r = self.client.post(reverse('profile.edit'), d, follow=True)

        assert 'You changed your username;' in r.content, (
                'User should know that changing their username changes '
                'their URL.')

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
        with browserid_mock.mock_browserid(email1):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        with browserid_mock.mock_browserid(email1):
            self.client.post(reverse('register'), register, follow=True)

        self.client.logout()
        # Create a different user
        email2 = 'coldfusion@gmail.com'
        register.update(email=email2)
        with browserid_mock.mock_browserid(email2):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        with browserid_mock.mock_browserid(email2):
            r = self.client.post(reverse('register'), register, follow=True)

        # Make sure we can't use the same username twice
        assert r.context['form'].errors, "Form should throw errors."
