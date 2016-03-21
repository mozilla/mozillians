from django.core.urlresolvers import reverse

from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.groups.models import GroupMembership, Invite
from mozillians.groups.tests import InviteFactory
from mozillians.users.tests import UserFactory


class InviteTest(TestCase):
    def test_accept_invitation_with_terms(self):
        inviter, redeemer = UserFactory.create_batch(2)
        invite = InviteFactory.create(inviter=inviter.userprofile, redeemer=redeemer.userprofile)
        invite.group.terms = 'Group Terms'
        invite.group.save()

        with self.login(redeemer) as client:
            url = reverse('groups:accept_reject_invitation', args=[invite.pk, 'accept'])
            response = client.get(url, follow=True)
            eq_(response.status_code, 200)

        invite = Invite.objects.get(pk=invite.pk)
        ok_(invite.accepted)
        ok_(invite.group.groupmembership_set.filter(userprofile=redeemer.userprofile,
                                                    status=GroupMembership.PENDING_TERMS).exists())

    def test_accept_invitation_without_terms(self):
        inviter, redeemer = UserFactory.create_batch(2)
        invite = InviteFactory.create(inviter=inviter.userprofile, redeemer=redeemer.userprofile)

        with self.login(redeemer) as client:
            url = reverse('groups:accept_reject_invitation', args=[invite.pk, 'accept'])
            response = client.get(url, follow=True)
            eq_(response.status_code, 200)

        invite = Invite.objects.get(pk=invite.pk)
        ok_(invite.accepted)
        ok_(invite.group.has_member(redeemer.userprofile))

    def test_reject_invitation(self):
        inviter, redeemer = UserFactory.create_batch(2)
        invite = InviteFactory.create(inviter=inviter.userprofile, redeemer=redeemer.userprofile)

        with self.login(redeemer) as client:
            url = reverse('groups:accept_reject_invitation', args=[invite.pk, 'reject'])
            response = client.get(url, follow=True)
            eq_(response.status_code, 200)

        invite = Invite.objects.filter(pk=invite.pk)
        ok_(not invite.exists())

    def test_accept_reject_user_not_redeemer(self):
        inviter, redeemer = UserFactory.create_batch(2)
        invite = InviteFactory.create(inviter=inviter.userprofile, redeemer=redeemer.userprofile)
        user = UserFactory.create()

        with self.login(user) as client:
            url = reverse('groups:accept_reject_invitation', args=[invite.pk, 'accept'])
            response = client.get(url, follow=True)
            eq_(response.status_code, 404)
