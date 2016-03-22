from django.core.urlresolvers import reverse

from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.groups.models import Invite
from mozillians.groups.tests import InviteFactory
from mozillians.users.tests import UserFactory


class InviteTest(TestCase):
    def test_accept_invitation(self):
        inviter, redeemer = UserFactory.create_batch(2)
        invite = InviteFactory.create(inviter=inviter.userprofile, redeemer=redeemer.userprofile)

        with self.login(redeemer) as client:
            url = reverse('groups:accept_invitation', kwargs={'invite_pk': invite.pk})
            response = client.get(url, follow=True)
            eq_(response.status_code, 200)

        invite = Invite.objects.get(pk=invite.pk)
        ok_(invite.accepted)
        ok_(invite.group.has_member(invite.redeemer))

    def test_reject_invitation(self):
        inviter, redeemer = UserFactory.create_batch(2)
        invite = InviteFactory.create(inviter=inviter.userprofile, redeemer=redeemer.userprofile)

        with self.login(redeemer) as client:
            url = reverse('groups:reject_invitation', kwargs={'invite_pk': invite.pk})
            response = client.get(url, follow=True)
            eq_(response.status_code, 200)

        invite = Invite.objects.get(pk=invite.pk)
        ok_(invite.accepted is False)
        ok_(not invite.group.has_member(invite.redeemer))

    def test_permissions_invitation_accept(self):
        inviter, redeemer = UserFactory.create_batch(2)
        invite = InviteFactory.create(inviter=inviter.userprofile, redeemer=redeemer.userprofile)
        user = UserFactory.create()

        with self.login(user) as client:
            url = reverse('groups:reject_invitation', kwargs={'invite_pk': invite.pk})
            response = client.get(url, follow=True)
            eq_(response.status_code, 404)
