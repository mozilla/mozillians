from mock import patch
from nose.tools import ok_

from mozillians.common.tests import TestCase
from mozillians.groups import signals
from mozillians.groups.models import GroupMembership
from mozillians.groups.tests import GroupFactory
from mozillians.users.tests import UserFactory


class SignalsTests(TestCase):
    def test_post_delete_membership(mock_cis):
        group = GroupFactory.create()
        user = UserFactory.create()

        # Assert that no group memberships exist
        ok_(GroupMembership.objects.all().count() == 0)

        group.add_member(user.userprofile, GroupMembership.MEMBER)

        # Assert that group memberships exist
        ok_(GroupMembership.objects.all().count() == 1)

        instance = GroupMembership.objects.all()[0]

        with patch('mozillians.users.tasks.send_userprofile_to_cis') as mock_cis:
            signals.delete_groupmembership(GroupMembership, instance)
            mock_cis.delay.assert_called_once_with(user.userprofile.pk)
