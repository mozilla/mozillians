from nose.tools import ok_

from mozillians.common.tests import TestCase
from mozillians.groups.forms import GroupForm
from mozillians.groups.tests import GroupAliasFactory, GroupFactory


class GroupFormTests(TestCase):
    def test_name_unique(self):
        group = GroupFactory.create()
        GroupAliasFactory.create(alias=group, name='bar')
        form = GroupForm({'name': 'bar'})
        ok_(not form.is_valid())
        ok_('name' in form.errors)
