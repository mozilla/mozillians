# -*- coding: utf-8 -*-
from datetime import datetime, timedelta

from django.conf import settings
from django.template.loader import get_template
from django.test import override_settings

from mock import patch, ANY
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.groups import tasks
from mozillians.groups.models import Group, GroupMembership, Skill
from mozillians.groups.tasks import invalidate_group_membership, email_membership_change
from mozillians.groups.tests import GroupFactory, InviteFactory, SkillFactory
from mozillians.users.tests import UserFactory


class SendPendingMembershipEmailsTests(TestCase):

    def test_remove_empty_groups(self):
        user = UserFactory.create()
        group_1 = GroupFactory.create()
        GroupFactory.create()
        skill_1 = SkillFactory.create()
        SkillFactory.create()

        group_1.add_member(user.userprofile)
        skill_1.members.add(user.userprofile)

        tasks.remove_empty_groups()

        eq_(Group.objects.all().count(), 1)
        ok_(Group.objects.filter(id=group_1.id).exists())
        eq_(Skill.objects.all().count(), 1)
        ok_(Skill.objects.filter(id=skill_1.id).exists())

    def test_sending_pending_email(self):
        # If a curated group has a pending membership, added since the reminder email
        # was last sent, send the curator an email.  It should contain the count of
        # all pending memberships.
        curator = UserFactory.create()
        group = GroupFactory.create()
        group.curators.add(curator.userprofile)

        # Add a couple of pending memberships
        group.add_member(UserFactory.create().userprofile, GroupMembership.PENDING)
        group.add_member(UserFactory.create().userprofile, GroupMembership.PENDING)

        with patch('mozillians.groups.tasks.send_mail', autospec=True) as mock_send_mail:
            tasks.send_pending_membership_emails()
        ok_(mock_send_mail.called)
        # Should only have been called once
        eq_(1, len(mock_send_mail.call_args_list))

        # The message body should mention that there are 2 pending memberships
        subject, body, from_addr, to_list = mock_send_mail.call_args[0]
        eq_('2 outstanding requests to join Mozillians group "%s"' % group.name, subject)
        ok_('There are 2 outstanding requests' in body)
        # Full path to group page is in the message
        ok_(group.get_absolute_url() in body)
        ok_(curator.email in to_list)

        # Add another pending membership
        group.add_member(UserFactory.create().userprofile, GroupMembership.PENDING)
        # Should send email again
        with patch('mozillians.groups.tasks.send_mail', autospec=True) as mock_send_mail:
            tasks.send_pending_membership_emails()
        ok_(mock_send_mail.called)

    def test_sending_pending_email_singular(self):
        # If a curated group has exactly one pending membership, added since the reminder email
        # was last sent, send the curator an email.  It should contain the count of
        # all pending memberships, which should be one, and should use the singular text.
        curator = UserFactory.create()
        group = GroupFactory.create()
        group.curators.add(curator.userprofile)

        # Add one pending membership
        group.add_member(UserFactory.create().userprofile, GroupMembership.PENDING)

        with patch('mozillians.groups.tasks.send_mail', autospec=True) as mock_send_mail:
            tasks.send_pending_membership_emails()
        ok_(mock_send_mail.called)

        # The message body should mention that there is 1 pending memberships
        subject, body, from_addr, to_list = mock_send_mail.call_args[0]
        eq_('1 outstanding request to join Mozillians group "%s"' % group.name, subject)
        ok_('There is 1 outstanding request' in body)
        # Full path to group page is in the message
        ok_(group.get_absolute_url() in body)
        ok_(curator.email in to_list)

    def test_sending_pending_email_already_sent(self):
        # If a curated group has a pending membership, but it was added before the
        # last time a reminder email was sent, do not send the curator an email.

        # curated group:
        group = GroupFactory.create()
        group.curators.add(UserFactory.create().userprofile)

        # Pending membership
        user1 = UserFactory.create()
        group.add_member(user1.userprofile, GroupMembership.PENDING)
        membership = GroupMembership.objects.get(userprofile=user1.userprofile, group=group)
        membership.save()

        # Send email. This should update the field remembering the max pending request pk.
        tasks.send_pending_membership_emails()

        # Non-pending membership
        user2 = UserFactory.create()
        group.add_member(user2.userprofile, GroupMembership.MEMBER)

        # None of this should trigger an email send
        with patch('mozillians.groups.tasks.send_mail', autospec=True) as mock_send_mail:
            tasks.send_pending_membership_emails()
        ok_(not mock_send_mail.called)

    def test_sending_pending_email_non_curated(self):
        # If a non-curated group has a pending membership,  do not send anyone an email
        group = GroupFactory.create()
        user = UserFactory.create()
        group.add_member(user.userprofile, GroupMembership.PENDING)
        with patch('mozillians.groups.tasks.send_mail', autospec=True) as mock_send_mail:
            tasks.send_pending_membership_emails()
        ok_(not mock_send_mail.called)


class EmailMembershipChangeTests(TestCase):
    def setUp(self):
        self.group = GroupFactory.create()
        self.group.curators.add(UserFactory.create().userprofile)
        self.user = UserFactory.create()

    def test_member_accepted(self):
        template_name = 'groups/email/accepted.txt'
        template = get_template(template_name)
        with patch('mozillians.groups.tasks.get_template', autospec=True) as mock_get_template:
            mock_get_template.return_value = template
            with patch('mozillians.groups.tasks.send_mail', autospec=True) as mock_send_mail:
                email_membership_change(self.group.pk, self.user.pk,
                                        GroupMembership.PENDING, GroupMembership.MEMBER)
        ok_(mock_send_mail.called)
        ok_(mock_get_template.called)
        eq_(template_name, mock_get_template.call_args[0][0])
        subject, body, from_addr, to_list = mock_send_mail.call_args[0]
        eq_(settings.FROM_NOREPLY, from_addr)
        eq_([self.user.email], to_list)
        eq_('Accepted to Mozillians group "%s"' % self.group.name, subject)
        ok_('You have been accepted' in body)

    def test_member_rejected(self):
        template_name = 'groups/email/rejected.txt'
        template = get_template(template_name)
        with patch('mozillians.groups.tasks.get_template', autospec=True) as mock_get_template:
            mock_get_template.return_value = template
            with patch('mozillians.groups.tasks.send_mail', autospec=True) as mock_send_mail:
                email_membership_change(self.group.pk, self.user.pk,
                                        GroupMembership.PENDING, None)
        ok_(mock_send_mail.called)
        ok_(mock_get_template.called)
        eq_(template_name, mock_get_template.call_args[0][0])
        subject, body, from_addr, to_list = mock_send_mail.call_args[0]
        eq_(settings.FROM_NOREPLY, from_addr)
        eq_([self.user.email], to_list)
        eq_('Not accepted to Mozillians group "%s"' % self.group.name, subject)
        ok_('You have not been accepted' in body)


class MembershipInvalidationTests(TestCase):
    """ Test membership invalidation."""

    @patch('mozillians.groups.tasks.send_mail')
    @override_settings(FROM_NOREPLY='noreply@example.com')
    def test_invalidate_group_with_terms(self, mock_send_mail):
        member = UserFactory.create(vouched=True)
        curator = UserFactory.create(vouched=True)

        group = GroupFactory.create(name='Foo', terms='Example terms.', invalidation_days=5)
        group.curators.add(curator.userprofile)
        group.add_member(member.userprofile)
        group.add_member(curator.userprofile)

        membership = group.groupmembership_set.filter(userprofile=member.userprofile)
        curator_membership = group.groupmembership_set.filter(userprofile=curator.userprofile)
        membership.update(updated_on=datetime.now() - timedelta(days=10))
        curator_membership.update(updated_on=datetime.now() - timedelta(days=10))

        eq_(membership[0].status, GroupMembership.MEMBER)
        eq_(curator_membership[0].status, GroupMembership.MEMBER)

        invalidate_group_membership()

        ok_(not group.groupmembership_set.filter(userprofile=member.userprofile).exists())
        ok_(group.groupmembership_set.filter(userprofile=curator.userprofile).exists())

        subject = 'Removed from Mozillians group "foo"'
        mock_send_mail.assert_called_once_with(subject, ANY, 'noreply@example.com',
                                               [member.email], fail_silently=False)

    @patch('mozillians.groups.tasks.send_mail')
    @override_settings(FROM_NOREPLY='noreply@example.com')
    def test_invalidate_group_by_request(self, mock_send_mail):
        member = UserFactory.create(vouched=True)
        curator = UserFactory.create(vouched=True)

        group = GroupFactory.create(name='Foo', invalidation_days=5,
                                    accepting_new_members='by_request')
        group.curators.add(curator.userprofile)
        group.add_member(curator.userprofile)
        group.add_member(member.userprofile)

        membership = group.groupmembership_set.filter(userprofile=member.userprofile)
        curator_membership = group.groupmembership_set.filter(userprofile=curator.userprofile)
        membership.update(updated_on=datetime.now() - timedelta(days=10))
        curator_membership.update(updated_on=datetime.now() - timedelta(days=10))

        eq_(membership[0].status, GroupMembership.MEMBER)
        eq_(curator_membership[0].status, GroupMembership.MEMBER)

        invalidate_group_membership()

        ok_(not group.groupmembership_set.filter(userprofile=member.userprofile).exists())
        ok_(group.groupmembership_set.filter(userprofile=curator.userprofile).exists())

        subject = 'Removed from Mozillians group "foo"'
        mock_send_mail.assert_called_once_with(subject, ANY, 'noreply@example.com',
                                               [member.email], fail_silently=False)

    @patch('mozillians.groups.tasks.send_mail')
    @override_settings(FROM_NOREPLY='noreply@example.com')
    def test_invalidate_group_accepts_all(self, mock_send_mail):
        member = UserFactory.create(vouched=True)
        curator = UserFactory.create(vouched=True)

        group = GroupFactory.create(name='Foo', invalidation_days=5)
        group.curators.add(curator.userprofile)
        group.add_member(curator.userprofile)
        group.add_member(member.userprofile)

        membership = group.groupmembership_set.filter(userprofile=member.userprofile)
        curator_membership = group.groupmembership_set.filter(userprofile=curator.userprofile)
        membership.update(updated_on=datetime.now() - timedelta(days=10))
        curator_membership.update(updated_on=datetime.now() - timedelta(days=10))

        eq_(membership[0].status, GroupMembership.MEMBER)
        eq_(curator_membership[0].status, GroupMembership.MEMBER)

        invalidate_group_membership()

        ok_(not group.groupmembership_set.filter(userprofile=member.userprofile).exists())
        ok_(group.groupmembership_set.filter(userprofile=curator.userprofile).exists())

        subject = 'Removed from Mozillians group "foo"'
        mock_send_mail.assert_called_once_with(subject, ANY, 'noreply@example.com',
                                               [member.email], fail_silently=False)


class InvitationEmailTests(TestCase):
    @patch('mozillians.groups.tasks.send_mail')
    @override_settings(FROM_NOREPLY='noreply@example.com')
    def test_send_invitation_email(self, mock_send_email):
        inviter, redeemer = UserFactory.create_batch(2)
        group = GroupFactory.create(name='Foo')
        template_name = 'groups/email/invite_email.txt'
        invite = InviteFactory.create(inviter=inviter.userprofile,
                                      redeemer=redeemer.userprofile,
                                      group=group)

        with patch('mozillians.groups.tasks.get_template', autospec=True) as mock_get_template:
            tasks.notify_redeemer_invitation(invite.pk)

        args = [
            '[Mozillians] You have been invited to join group "foo"',
            ANY,
            'noreply@example.com',
            [redeemer.userprofile.email]
        ]
        ok_(mock_get_template.called)
        eq_(template_name, mock_get_template.call_args[0][0])
        mock_send_email.assert_called_once_with(*args)

    @patch('mozillians.groups.tasks.send_mail')
    @override_settings(FROM_NOREPLY='noreply@example.com')
    def test_send_invitation_accepted_email(self, mock_send_email):
        inviter = UserFactory.create()
        redeemer = UserFactory.create(userprofile={'full_name': u'fôô bar'})
        group = GroupFactory.create(name='Foo')
        template_name = 'groups/email/invite_accepted_email.txt'
        invite = InviteFactory.create(inviter=inviter.userprofile,
                                      redeemer=redeemer.userprofile,
                                      group=group)

        with patch('mozillians.groups.tasks.get_template', autospec=True) as mock_get_template:
            tasks.notify_curators_invitation_accepted(invite.pk)
        args = [u'[Mozillians] fôô bar has accepted your invitation to join group "foo"',
                ANY,
                'noreply@example.com',
                [inviter.userprofile.email]]
        ok_(mock_get_template.called)
        eq_(template_name, mock_get_template.call_args[0][0])
        mock_send_email.assert_called_once_with(*args)

    @patch('mozillians.groups.tasks.send_mail')
    @override_settings(FROM_NOREPLY='noreply@example.com')
    def test_send_invitation_rejected_email(self, mock_send_email):
        inviter = UserFactory.create()
        redeemer = UserFactory.create(userprofile={'full_name': u'fôô bar'})
        group = GroupFactory.create(name='Foo')
        template_name = 'groups/email/invite_rejected_email.txt'
        InviteFactory.create(inviter=inviter.userprofile, redeemer=redeemer.userprofile,
                             group=group)
        with patch('mozillians.groups.tasks.get_template', autospec=True) as mock_get_template:
            args = [redeemer.userprofile.pk, inviter.userprofile.pk, group.pk]
            tasks.notify_curators_invitation_rejected(*args)
        args = [u'[Mozillians] fôô bar has rejected your invitation to join group "foo"',
                ANY,
                'noreply@example.com',
                [inviter.userprofile.email]]
        ok_(mock_get_template.called)
        eq_(template_name, mock_get_template.call_args[0][0])
        mock_send_email.assert_called_once_with(*args)

    @patch('mozillians.groups.tasks.send_mail')
    @override_settings(FROM_NOREPLY='noreply@example.com')
    def test_send_invitation_invalid_email(self, mock_send_email):
        inviter, redeemer = UserFactory.create_batch(2)
        group = GroupFactory.create(name='Foo')
        template_name = 'groups/email/invite_invalid_email.txt'
        InviteFactory.create(inviter=inviter.userprofile,
                             redeemer=redeemer.userprofile,
                             group=group)
        with patch('mozillians.groups.tasks.get_template', autospec=True) as mock_get_template:
            tasks.notify_redeemer_invitation_invalid(redeemer.userprofile.pk, group.pk)
        args = [
            '[Mozillians] Invitation to group "foo" is no longer valid',
            ANY,
            'noreply@example.com',
            [redeemer.userprofile.email]
        ]
        ok_(mock_get_template.called)
        eq_(template_name, mock_get_template.call_args[0][0])
        mock_send_email.assert_called_once_with(*args)
