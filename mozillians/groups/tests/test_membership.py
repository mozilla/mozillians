from mock import patch
from django.core import mail
from django.core.urlresolvers import reverse

from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.groups.models import GroupMembership
from mozillians.groups.tests import GroupFactory
from mozillians.users.tests import UserFactory


class TestGroupRemoveMember(TestCase):
    def setUp(self):
        self.group = GroupFactory()
        self.member = UserFactory()
        self.group.add_member(self.member.userprofile)
        self.url = reverse('groups:remove_member', prefix='/en-US/',
                           kwargs={'url': self.group.url,
                                   'user_pk': self.member.userprofile.pk})

    def test_as_manager(self):
        # manager can remove another from a group they're not curator of
        user = UserFactory(manager=True)
        with self.login(user) as client:
            response = client.post(self.url, follow=False)
        eq_(302, response.status_code)
        ok_(not self.group.has_member(self.member))

    def test_as_manager_from_unleavable_group(self):
        # manager can remove people even from unleavable groups
        user = UserFactory(manager=True)
        with self.login(user) as client:
            response = client.post(self.url, follow=False)
        eq_(302, response.status_code)
        ok_(not self.group.has_member(self.member))

    def test_as_manager_removing_curator(self):
        # but even manager cannot remove a curator
        user = UserFactory(manager=True)
        self.group.curator = self.member.userprofile
        self.group.save()
        with self.login(user) as client:
            response = client.post(self.url, follow=False)
        eq_(302, response.status_code)
        ok_(self.group.has_member(self.member))

    def test_as_simple_user_removing_self(self):
        # user can remove themselves
        with self.login(self.member) as client:
            response = client.post(self.url, follow=False)
        eq_(302, response.status_code)
        ok_(not self.group.has_member(self.member))

    def test_as_simple_user_removing_self_from_unleavable_group(self):
        # user cannot leave an unleavable group
        self.group.members_can_leave = False
        self.group.save()
        with self.login(self.member) as client:
            response = client.post(self.url, follow=False)
        eq_(302, response.status_code)
        ok_(self.group.has_member(self.member))

    def test_as_simple_user_removing_another(self):
        # user cannot remove anyone else
        user = UserFactory()
        with self.login(user) as client:
            response = client.post(self.url, follow=False)
        eq_(404, response.status_code)

    def test_as_curator(self):
        # curator can remove another
        curator = UserFactory()
        self.group.curator = curator.userprofile
        self.group.save()
        with self.login(curator) as client:
            response = client.post(self.url, follow=False)
        eq_(302, response.status_code)
        ok_(not self.group.has_member(self.member))

    def test_as_curator_twice(self):
        # removing a second time doesn't blow up
        curator = UserFactory()
        self.group.curator = curator.userprofile
        self.group.save()
        with self.login(curator) as client:
            client.post(self.url, follow=False)
            client.post(self.url, follow=False)

    def test_as_curator_from_unleavable(self):
        # curator can remove another even from an unleavable group
        self.group.members_can_leave = False
        self.group.save()
        curator = UserFactory()
        self.group.curator = curator.userprofile
        self.group.save()
        with self.login(curator) as client:
            response = client.post(self.url, follow=False)
        eq_(302, response.status_code)
        ok_(not self.group.has_member(self.member))

    def test_accepting_sends_email(self):
        # when curator accepts someone, they are sent an email
        curator = UserFactory()
        self.group.curator = curator.userprofile
        self.group.save()
        user = UserFactory()
        self.group.add_member(user.userprofile, GroupMembership.PENDING)
        # no email when someone makes membership request
        eq_(0, len(mail.outbox))
        # Using French for curator page to make sure that doesn't affect the language
        # that is used to email the member.
        url = reverse('groups:confirm_member', args=[self.group.url, user.userprofile.pk],
                      prefix='/fr/')
        with patch('mozillians.groups.models.email_membership_change', autospec=True) as mock_email:
            with self.login(curator) as client:
                response = client.post(url, follow=False)
        eq_(302, response.status_code)
        # email sent for curated group
        ok_(mock_email.delay.called)
        group_pk, user_pk, old_status, new_status = mock_email.delay.call_args[0]
        eq_(self.group.pk, group_pk)
        eq_(user.pk, user_pk)
        eq_(GroupMembership.PENDING, old_status)
        eq_(GroupMembership.MEMBER, new_status)

    def test_rejecting_sends_email(self):
        # when curator rejects someone, they are sent an email
        curator = UserFactory()
        self.group.curator = curator.userprofile
        self.group.save()
        user = UserFactory()
        self.group.add_member(user.userprofile, GroupMembership.PENDING)
        # no email when someone makes request
        eq_(0, len(mail.outbox))
        # Using French for curator page to make sure that doesn't affect the language
        # that is used to email the member.
        url = reverse('groups:remove_member', args=[self.group.url, user.userprofile.pk],
                      prefix='/fr/',)
        with patch('mozillians.groups.models.email_membership_change', autospec=True) as mock_email:
            with self.login(curator) as client:
                response = client.post(url, follow=False)
        eq_(302, response.status_code)
        # email sent for curated group
        ok_(mock_email.delay.called)
        group_pk, user_pk, old_status, new_status = mock_email.delay.call_args[0]
        eq_(self.group.pk, group_pk)
        eq_(user.pk, user_pk)
        eq_(GroupMembership.PENDING, old_status)
        ok_(new_status is None)

    def test_remove_member_send_mail(self):
        # when curator remove someone, sent mail to member
        curator = UserFactory()
        self.group.curator = curator.userprofile
        self.group.save()
        user = UserFactory()
        self.group.add_member(user.userprofile)
        url = reverse('groups:remove_member', args=[self.group.url, user.userprofile.pk],
                      prefix='/fr/',)
        with patch('mozillians.groups.models.member_removed_email', autospec=True) as mock_email:
            with self.login(curator) as client:
                response = client.post(url, follow=False)
        eq_(302, response.status_code)
        # email sent for curated group
        ok_(mock_email.delay.called)
        group_pk, user_pk, old_status = mock_email.delay.call_args[0]
        eq_(self.group.pk, group_pk)
        eq_(user.pk, user_pk)
