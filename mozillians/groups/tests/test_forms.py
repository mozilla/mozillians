from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.groups.forms import GroupForm, SuperuserGroupForm
from mozillians.groups.tests import GroupAliasFactory, GroupFactory


class GroupFormTests(TestCase):
    def test_name_unique(self):
        group = GroupFactory.create()
        GroupAliasFactory.create(alias=group, name='bar')
        form = GroupForm({'name': 'bar'})
        ok_(not form.is_valid())
        ok_('name' in form.errors)


class SuperuserGroupFormTests(TestCase):
    def test_by_request_group_without_new_member_criteria(self):
        form_data = {'name': 'test group', 'accepting_new_members': 'by_request'}
        form = SuperuserGroupForm(data=form_data)
        eq_(False, form.is_valid())
        ok_('new_member_criteria' in form.errors)

    def test_by_request_group_with_new_member_criteria(self):
        form_data = {'name': 'test group',
                     'accepting_new_members': 'by_request',
                     'new_member_criteria': 'some criteria'}
        form = SuperuserGroupForm(data=form_data)
        ok_(form.is_valid())
        ok_('new_member_criteria' in form.cleaned_data)

    def test_no_saved_criteria(self):
        form_data = {'name': 'test group',
                     'accepting_new_members': 'no',
                     'new_member_criteria': 'some criteria'}
        form = SuperuserGroupForm(data=form_data)
        ok_(form.is_valid())
        eq_(u'', form.cleaned_data['new_member_criteria'])
