from mock import patch
from django.template.loader import get_template
from mozillians.groups.tasks import email_membership_change
from nose.tools import eq_, ok_

from django.conf import settings

from mozillians.common.tests import TestCase
from mozillians.groups import tasks
from mozillians.groups.models import Group, GroupMembership, Skill
from mozillians.groups.tests import GroupFactory, SkillFactory
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
        group = GroupFactory.create(curator=curator.userprofile)

        # Add a couple of pending memberships
        group.add_member(UserFactory.create().userprofile, GroupMembership.PENDING)
        group.add_member(UserFactory.create().userprofile, GroupMembership.PENDING)

        with patch('mozillians.groups.tasks.send_mail', autospec=True) as mock_send_mail:
            tasks.send_pending_membership_emails()
        ok_(mock_send_mail.called)

        # The message body should mention that there are 2 pending memberships
        subject, body, from_addr, to_list = mock_send_mail.call_args[0]
        eq_('2 outstanding requests to join Mozillians group "%s"' % group.name, subject)
        ok_('There are 2 outstanding requests' in body)
        # Full path to group page is in the message
        ok_(group.get_absolute_url() in body)
        print("to_list=%s, curator.email=%s" % (to_list, curator.email))
        ok_(curator.email in to_list)

        # Add another pending membership
        group.add_member(UserFactory.create().userprofile, GroupMembership.PENDING)
        # Should send email again
        with patch('mozillians.groups.tasks.send_mail', autospec=True) as mock_send_mail:
            tasks.send_pending_membership_emails()
        ok_(mock_send_mail.called)

    def test_sending_pending_email_already_sent(self):
        # If a curated group has a pending membership, but it was added before the
        # last time a reminder email was sent, do not send the curator an email.

        # curated group:
        group = GroupFactory.create(curator=UserFactory.create().userprofile)

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
        self.group = GroupFactory.create(curator=UserFactory.create().userprofile)
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
