from django.contrib.admin.sites import site
from django.http import HttpRequest

from mock import Mock
from nose.tools import eq_

from mozillians.common.tests import TestCase
from mozillians.groups.admin import GroupAdmin
from mozillians.groups.models import Group
from mozillians.groups.tests import GroupFactory
from mozillians.users.tests import UserFactory


class TestGroupAdmin(TestCase):
    def test_member_counts(self):
        # The Group admin computes how many vouched members there are
        # and how many overall

        # IMPORTANT: This test is expected to fail on Postgres, and
        # probably other databases where the Boolean type is not just
        # an alias for a small integer. Mozillians is currently
        # deployed on a database where this works. If we ever try
        # deploying it on another database where it doesn't work, this
        # test will alert us quickly that we'll need to take another
        # approach to this feature.

        # Create group with 1 vouched member and 1 unvouched member
        group = GroupFactory()
        user = UserFactory(userprofile={'is_vouched': False})
        group.add_member(user.userprofile)
        user2 = UserFactory(userprofile={'is_vouched': True})
        group.add_member(user2.userprofile)

        admin = GroupAdmin(model=Group, admin_site=site)
        mock_request = Mock(spec=HttpRequest)
        qset = admin.queryset(mock_request)

        g = qset.get(name=group.name)
        eq_(2, g.member_count)
        eq_(1, g.vouched_member_count)
