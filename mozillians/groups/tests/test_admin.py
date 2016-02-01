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
        group = GroupFactory()
        user = UserFactory.create()
        group.add_member(user.userprofile)
        admin = GroupAdmin(model=Group, admin_site=site)
        mock_request = Mock(spec=HttpRequest)
        qset = admin.get_queryset(mock_request)

        g = qset.get(name=group.name)
        eq_(1, g.member_count)
