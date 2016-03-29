from django.core.urlresolvers import reverse

from mock import patch, ANY
from nose.tools import eq_, ok_

from mozillians.common.templatetags.helpers import urlparams
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

    @patch('mozillians.groups.views.notify_redeemer_invitation')
    @patch('mozillians.groups.views.messages.success')
    def test_send_invitation_email(self, mock_success, mock_notification):
        curator = UserFactory.create()
        redeemer = UserFactory.create(userprofile={'full_name': 'Foo Bar'})
        invite = InviteFactory.create(inviter=curator.userprofile, redeemer=redeemer.userprofile)
        invite.group.curators.add(curator.userprofile)

        with self.login(curator) as client:
            url = urlparams(reverse('groups:send_invitation_email',
                                    args=[invite.pk]), 'invitation')
            response = client.get(url, follow=True)
            eq_(response.status_code, 200)

        mock_notification.delay.assert_called_once_with(invite.pk, '')
        msg = 'Invitation to Foo Bar has been sent successfully.'
        mock_success.assert_called_once_with(ANY, msg)

    @patch('mozillians.groups.views.notify_redeemer_invitation')
    @patch('mozillians.groups.views.messages.success')
    def test_send_invitation_email_custom_text(self, mock_success, mock_notification):
        curator = UserFactory.create()
        redeemer = UserFactory.create(userprofile={'full_name': 'Foo Bar'})
        invite = InviteFactory.create(inviter=curator.userprofile, redeemer=redeemer.userprofile)
        invite.group.invite_email_text = 'Foo bar'
        invite.group.save()
        invite.group.curators.add(curator.userprofile)

        with self.login(curator) as client:
            url = urlparams(reverse('groups:send_invitation_email',
                                    args=[invite.pk]), 'invitation')
            response = client.get(url, follow=True)
            eq_(response.status_code, 200)

        mock_notification.delay.assert_called_once_with(invite.pk, 'Foo bar')
        msg = 'Invitation to Foo Bar has been sent successfully.'
        mock_success.assert_called_once_with(ANY, msg)

    @patch('mozillians.groups.views.notify_redeemer_invitation')
    @patch('mozillians.groups.views.messages.success')
    def test_send_invitation_email_different_curator(self, mock_success, mock_notification):
        curator, inviter = UserFactory.create_batch(2)
        redeemer = UserFactory.create(userprofile={'full_name': 'Foo Bar'})
        invite = InviteFactory.create(inviter=inviter.userprofile, redeemer=redeemer.userprofile)
        invite.group.curators.add(curator.userprofile)
        invite.group.curators.add(inviter.userprofile)

        with self.login(curator) as client:
            url = urlparams(reverse('groups:send_invitation_email',
                                    args=[invite.pk]), 'invitation')
            response = client.get(url, follow=True)
            eq_(response.status_code, 200)

        mock_notification.delay.assert_called_once_with(invite.pk, '')
        msg = 'Invitation to Foo Bar has been sent successfully.'
        mock_success.assert_called_once_with(ANY, msg)

    def test_send_invitation_email_no_curator_manager(self):
        inviter, redeemer = UserFactory.create_batch(2)
        invite = InviteFactory.create(inviter=inviter.userprofile, redeemer=redeemer.userprofile)
        user = UserFactory.create()

        with self.login(user) as client:
            url = urlparams(reverse('groups:send_invitation_email',
                                    args=[invite.pk]), 'invitation')
            response = client.get(url, follow=True)
            eq_(response.status_code, 404)
