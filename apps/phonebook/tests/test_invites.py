from django.core import mail
from django.contrib.auth.models import User

from nose.tools import eq_
from pyquery import PyQuery as pq

import common.tests
from funfactory.urlresolvers import reverse
from phonebook.models import Invite


class InviteTest(common.tests.TestCase):
    def invite_someone(self, email):
        """
        This method will invite a user.

        This will verify that an email with link has been sent.
        """
        # Send an invite.
        url = reverse('invite')
        d = dict(recipient=email)
        r = self.mozillian_client.post(url, d, follow=True)
        eq_(r.status_code, 200)
        assert ('%s has been invited to Mozillians.' % email in
                pq(r.content)('div#main-content p').text())

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

    def redeem_invite(self, invite, **kw):
        """Given an invite_url go to it and redeem an invite."""
        # Now let's look at the register form.
        self.client.logout()
        d = kw

        self.client.get(invite.get_url(), follow=True)
        self.client.post(reverse('browserid_verify'), d, follow=True)

        # Now let's register
        d.update(
                first_name='Akaaaaaaash',
                last_name='Desaaaaaaai',
                optin=True
                )

        r = self.client.post(reverse('register'), d, follow=True)

        u = User.objects.get(email=d['email']).get_profile()
        u.is_confirmed = True
        u.save()

        return r

    def test_send_invite_flow(self):
        return
        """
        Test the invitation flow.

        Send an invite.  See that email is sent.
        See that link allows us to sign in and be auto-vouched.
        Verify that we can't reuse the invite_url
        Verify we can't reinvite a vouched user
        """
        email = 'mr.fusion@gmail.com'
        assertion = 'mrfusionsomereallylongstring'
        invite = self.invite_someone(email)
        d = dict(assertion=assertion, email=email, mode='register')

        r = self.get_register(invite)
        self.redeem_invite(invite, username='ad', **d)

        profile = Invite.objects.get(pk=invite.pk).redeemer
        eq_(profile.is_vouched, True)

        # Don't reuse codes.
        self.redeem_invite(invite, username='ad2', email='mr2@gmail.com')
        eq_(User.objects.get(email='mr2@gmail.com').get_profile().is_vouched,
            False)

        # Don't reinvite a vouched user
        url = reverse('invite')
        d = dict(recipient='mr.fusion@gmail.com')
        self.client.login(email=self.mozillian.email)
        r = self.client.post(url, d, follow=True)
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
