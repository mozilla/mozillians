from django.contrib.auth.models import User
from django.core import mail

from nose.tools import eq_
from pyquery import PyQuery as pq

from common.browserid_mock import mock_browserid
import common.tests
from funfactory.urlresolvers import reverse
from phonebook.models import Invite


class InviteFlowTest(common.tests.TestCase):
    fake_email = 'mr.fusion@gmail.com'
    fake_email2 = 'mrs.fusion@gmail.com'

    # Assertion doesn't matter since we monkey patched it for testing
    fake_assertion = 'mrfusionsomereallylongstring'
    fake_invite_message = 'Join Mozilla'

    def invite_someone(self, email, invite_message):
        """
        This method will invite a user.

        This will verify that an email with link has been sent.
        """
        # Send an invite.
        url = reverse('invite')
        d = dict(recipient=email, message=invite_message)
        r = self.mozillian_client.post(url, d, follow=True)
        eq_(r.status_code, 200)
        assert ('%s has been invited to Mozillians.' % email in
                pq(r.content)('div#main p').text())

        # See that the email was sent.
        eq_(len(mail.outbox), 1)

        i = Invite.objects.get()
        invite_url = i.get_url()

        assert 'no-reply@mozillians.org' in mail.outbox[0].from_email
        assert invite_url in mail.outbox[0].body, "No link in email."
        return i

    def get_register(self, invite):
        r = self.client.get(invite.get_url(), follow=True)
        eq_(self.client.session['invite-code'], invite.code)
        return r

    def redeem_invite(self, invite, email):
        """Given an invite_url go to it and redeem an invite."""
        # Lets make sure we have a clean slate
        self.client.logout()
        assert (not User.objects.filter(email=email),
                    "User shouldn't be in database.")

        # We need to store the invite code in the session
        self.client.get(invite.get_url(), follow=True)

        # BrowserID needs an assertion not to be whiney
        d = dict(assertion=self.fake_assertion)
        with mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        # Now let's register
        d = dict(
            first_name='Akaaaaaaash',
            last_name='Desaaaaaaai',
            optin=True
        )
        with mock_browserid(email):
            self.client.post(reverse('register'), d, follow=True)

        # Return the New Users Profile
        invited_user_profile = User.objects.get(email=email).get_profile()
        return invited_user_profile

    def invite_without_message(self, email):
        """
        Make sure we can send an invite without the optional personal
        message and that the template doesn't use Personal message:
        when there's no personal message.
        """
        # Send an invite without a personal message.
        url = reverse('invite')
        d = dict(recipient=email)
        r = self.mozillian_client.post(url, d, follow=True)
        eq_(r.status_code, 200)
        assert ('%s has been invited to Mozillians.' % email in
                pq(r.content)('div#main p').text())

        # See that the email was sent.
        eq_(len(mail.outbox), 2)

        # Note it's mail.outbox[1] here because we're sending another
        # message in a previous test.
        assert not ("Personal message" in mail.outbox[1].body)

    def test_send_invite_flow(self):
        """
        Test the invitation flow.

        Send an invite.  See that email is sent.
        See that link allows us to sign in and be auto-vouched.
        Verify that we can't reuse the invite_url
        Verify we can't reinvite a vouched user
        """
        invite = self.invite_someone(self.fake_email, self.fake_invite_message)
        self.invite_without_message(self.fake_email)
        self.get_register(invite)
        invited_user_profile = self.redeem_invite(invite, self.fake_email)
        assert(invited_user_profile.is_vouched)
        assert(invite.inviter == invited_user_profile.vouched_by)

        # Don't reuse codes.
        self.redeem_invite(invite, email='mr2@gmail.com')
        eq_(User.objects.get(email='mr2@gmail.com').get_profile().is_vouched,
            False)


class InviteEdgeTest(common.tests.TestCase):

    def test_no_reinvite(self):
        """Don't reinvite a vouched user."""
        vouched_email = 'mr.fusion@gmail.com'
        create_vouched_user(vouched_email)
        url = reverse('invite')
        d = dict(recipient=vouched_email)
        r = self.mozillian_client.post(url, d, follow=True)
        eq_(r.status_code, 200)
        assert ('You cannot invite someone who has already been vouched.' in
                pq(r.content)('ul.errorlist li').text())

    def test_unvouched_cant_invite(self):
        """
        Let's make sure the unvouched don't let in their friends...

        Their stupid friends...
        """
        url = reverse('invite')
        d = dict(recipient='mr.fusion@gmail.com')
        self.client.login(email=self.pending.email)
        r = self.client.post(url, d, follow=True)
        eq_(r.status_code, 403)


def create_vouched_user(email):
        user = User.objects.create(
                email=email,
                username=email,
                first_name='Amandeep',
                last_name='McIlrath')
        profile = user.get_profile()
        profile.is_vouched = True
        profile.save()
        return user
