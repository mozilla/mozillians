from django.core import mail
from django.contrib.auth.models import User

from nose.tools import eq_
from pyquery import PyQuery as pq

from funfactory.urlresolvers import reverse
from phonebook.models import Invite
from phonebook.tests import LDAPTestCase


class InviteTest(LDAPTestCase):
    def invite_someone(self):
        """
        This method will invite a user.

        This will verify that an email with link has been sent.
        """
        # Send an invite.
        url = reverse('invite')
        d = dict(recipient='mr.fusion@gmail.com')
        r = self.mozillian_client.post(url, d, follow=True)
        eq_(r.status_code, 200)
        assert ('mr.fusion@gmail.com has been invited to Mozillians.' in
                pq(r.content)('div#main-content p').text())

        # See that the email was sent.
        eq_(len(mail.outbox), 1)

        i = Invite.objects.get()
        invite_url = i.get_url()

        assert 'no-reply@mozillians.org' in mail.outbox[0].from_email
        assert invite_url in mail.outbox[0].body, "No link in email."
        return i

    def get_register(self, invite):
        r = self.client.get(invite.get_url())
        doc = pq(r.content)
        eq_(doc('input#id_email')[0].value, invite.recipient)
        eq_(doc('input#id_code')[0].value, invite.code)
        return r

    def redeem_invite(self, invite, **kw):
        """Given an invite_url go to it and redeem an invite."""
        # Now let's look at the register form.
        self.client.logout()
        d = kw

        # Now let's register
        d.update(
                first_name='Akaaaaaaash',
                last_name='Desaaaaaaai',
                password='tacoface',
                confirmp='tacoface',
                optin=True
                )

        self.client.post(invite.get_url(), d, follow=True)

        u = User.objects.filter(email=d['email'])[0].get_profile()
        u.is_confirmed = True
        u.save()

        return self.client.post(reverse('login'),
                                dict(username=d['email'],
                                     password=d['password']),
                                follow=True)

    def test_send_invite_flow(self):
        """
        Test the invitation flow.

        Send an invite.  See that email is sent.
        See that link allows us to sign in and be auto-vouched.
        Verify that we can't reuse the invite_url
        Verify we can't reinvite a vouched user
        """
        invite = self.invite_someone()
        r = self.get_register(invite)
        d = r.context['form'].initial

        r = self.redeem_invite(invite, **d)

        eq_(r.context['user'].get_profile().is_vouched, True)
        eq_(r.context['user'].get_profile(),
            Invite.objects.get(pk=invite.pk).redeemer)

        # Don't reuse codes.
        r = self.redeem_invite(invite, email='mr2@gmail.com')
        eq_(r.context['user'].get_profile().is_vouched, False)

        # Don't reinvite a vouched user
        url = reverse('invite')
        d = dict(recipient='mr.fusion@gmail.com')
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
        r = self.pending_client.post(url, d, follow=True)
        eq_(r.status_code, 403)
