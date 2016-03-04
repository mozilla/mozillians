from django.core.urlresolvers import reverse

from mock import patch
from nose.tools import eq_

from mozillians.common.tests import TestCase
from mozillians.groups.tests import InviteFactory
from mozillians.users.tests import UserFactory


class InviteTest(TestCase):
    @patch('mozillians.groups.views.Invite.accept')
    def test_accept_invitation(self, mock_accept):
        inviter, redeemer = UserFactory.create_batch(2)
        invite = InviteFactory.create(inviter=inviter.userprofile, redeemer=redeemer.userprofile)

        with self.login(redeemer) as client:
            url = reverse('groups:accept_invitation', kwargs={'invite_pk': invite.pk})
            response = client.get(url, follow=True)
            eq_(response.status_code, 200)
            invite.accept.assert_called_once_with()

    @patch('mozillians.groups.views.Invite.reject')
    def test_reject_invitation(self, mock_accept):
        inviter, redeemer = UserFactory.create_batch(2)
        invite = InviteFactory.create(inviter=inviter.userprofile, redeemer=redeemer.userprofile)

        with self.login(redeemer) as client:
            url = reverse('groups:reject_invitation', kwargs={'invite_pk': invite.pk})
            response = client.get(url, follow=True)
            eq_(response.status_code, 200)
            invite.reject.assert_called_once_with()
