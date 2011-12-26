from django.core import mail
from django.contrib.auth.models import User

from funfactory.urlresolvers import reverse
from nose.tools import eq_
from pyquery import PyQuery as pq

from common.tests import ESTestCase, TestCase
from groups.models import Group
from users.models import UserProfile

Group.objects.get_or_create(name='staff', system=True)


class ViewTest(TestCase):
    """Test views in the users app."""

    def test_confirmation_code(self):
        """Verify the confirm view accepts valid codes and 404s otherwise."""
        d = dict(
                 email='mrfusion@gmail.com',
                 first_name='Akaaaaaaash',
                 last_name='Desaaaaaaai',
                 password='tacoface',
                 confirmp='tacoface',
                 optin=True
                )
        r = self.client.post(reverse('register'), d, follow=True)
        user = User.objects.filter(email=d['email'])[0].get_profile()
        user.get_confirmation_url()

        r = self.client.get(reverse('confirm'))
        eq_(r.status_code, 404, 'No confirmation code raises a 404.')

        r = self.client.get(reverse('confirm') + '?code=badcode')
        eq_(r.status_code, 404, 'A bad confirmation code raises a 404.')

        r = self.client.get(user.get_confirmation_url())
        eq_(r.status_code, 200, 'A good confirmation code works.')


class RegistrationTest(TestCase):
    """Tests registration."""

    def test_confirmation(self):
        """Verify confirmation.

        When a user registers they:

        * Must be sent a confirmation email.
        * May not log in.
        * May confirm their email.
        * May then log in.
        """
        # Now let's register
        d = dict(
                 email='mrfusion@gmail.com',
                 first_name='Akaaaaaaash',
                 last_name='Desaaaaaaai',
                 password='tacoface',
                 confirmp='tacoface',
                 optin=True
                )
        r = self.client.post(reverse('register'), d, follow=True)
        eq_(len(mail.outbox), 1)
        u = User.objects.filter(email=d['email'])[0].get_profile()
        assert u.get_confirmation_url() in mail.outbox[0].body

        r = self.client.post(reverse('login'),
                             dict(username=d['email'], password=d['password']))
        assert ('You need to confirm your account before you can log in.' in
                r.context['form'].errors['__all__'][0])

        r = self.client.get(u.get_confirmation_url())
        assert "Your email address has been confirmed." in r.content

        r = self.client.post(reverse('login'),
                             dict(username=d['email'], password=d['password']),
                             follow=True)
        eq_(d['email'], str(r.context['user']))

        assert not (r.context['user'].get_profile().groups
                     .filter(name='staff')), (
                    'Regular user should not belong to the "staff" group.')

    def test_mozillacom_registration(self):
        """Verify @mozilla.com users are auto-vouched and marked "staff"."""
        d = dict(
                 email='mrfusion@mozilla.com',
                 first_name='Akaaaaaaash',
                 last_name='Desaaaaaaai',
                 password='tacoface',
                 confirmp='tacoface',
                 optin=True
        )
        r = self.client.post(reverse('register'), d, follow=True)
        eq_(len(mail.outbox), 1)
        u = User.objects.filter(email=d['email'])[0].get_profile()
        assert u.get_confirmation_url() in mail.outbox[0].body

        r = self.client.post(reverse('login'),
                             dict(username=d['email'], password=d['password']))
        assert ('You need to confirm your account before you can log in.' in
                r.context['form'].errors['__all__'][0])

        r = self.client.get(u.get_confirmation_url())
        assert "Your email address has been confirmed." in r.content

        r = self.client.post(reverse('login'),
                             dict(username=d['email'], password=d['password']),
                             follow=True)
        doc = pq(r.content)

        eq_(d['email'], str(r.context['user']))
        assert r.context['user'].get_profile().is_vouched, (
                "Moz.com should be auto-vouched")

        assert not doc('#pending-approval'), (
                'Moz.com profile page should not having pending vouch div.')

        assert r.context['user'].get_profile().groups.filter(name='staff'), (
                'Moz.com should belong to the "staff" group.')

    def test_mozillacom_registration_case_insensitive_username(self):
        """Verify @mozilla.com users can sign up only once with the same email.
        """
        d = dict(
                 email='mRfUsIoN@mozilla.com',
                 first_name='Akaaaaaaash',
                 last_name='Desaaaaaaai',
                 password='tacoface',
                 confirmp='tacoface',
                 optin=True
        )
        # once
        self.client.post(reverse('register'), d, follow=True)
        eq_(len(mail.outbox), 1)
        # twice
        r = self.client.post(reverse('register'), d, follow=True)
        assert r.context['form'].errors, "Form should throw errors."
        eq_(len(mail.outbox), 1)

    def test_plus_signs(self):
        d = dict(
                 email='mrfusion+dotcom@mozilla.com',
                 first_name='Akaaaaaaash',
                 last_name='Desaaaaaaai',
                 password='tacoface',
                 confirmp='tacoface',
                 optin=True
        )
        r = self.client.post(reverse('register'), d, follow=True)
        eq_(len(mail.outbox), 1)
        u = User.objects.filter(email=d['email'])[0].get_profile()
        assert u.get_confirmation_url() in mail.outbox[0].body

        r = self.client.post(u.get_send_confirmation_url())
        eq_(r.status_code, 200)


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
        r = self.client.get(reverse('register'))
        self.assertTrue(200 == r.status_code,
                        'Anonymous users can access the registration page')

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
        r = self.mozillian_client.get(reverse('phonebook.search'),
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
        r = self.mozillian_client.get(reverse('phonebook.search'),
                                      {'q': self.pending.email})
        assert 'Mozillian' in r.content, (
                'User should appear as a Mozillian in search.')
