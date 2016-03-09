from nose.tools import eq_

from mozillians.common.tests import TestCase
from mozillians.groups.templatetags.helpers import stringify_groups
from mozillians.groups.models import Group
from mozillians.groups.tests import GroupFactory


class HelperTests(TestCase):
    def test_stringify_groups(self):
        GroupFactory.create(name='abc')
        GroupFactory.create(name='def')
        groups = Group.objects.all()
        result = stringify_groups(groups)
        eq_(result, 'abc,def')
