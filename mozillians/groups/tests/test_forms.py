# -*- coding: utf-8 -*-
from nose.tools import eq_, ok_

from mozillians.groups.forms import SuperuserGroupForm
from mozillians.common.tests import TestCase


class SuperuserGroupFormTests(TestCase):

    def test_required_moderation(self):
        form_data = {'name': 'test group'}
        form = SuperuserGroupForm(data=form_data)
        eq_(False, form.is_valid())
        ok_('accepting_new_members' in form.errors)

        form_data = {'name': 'test group', 'accepting_new_members': 'yes'}
        form = SuperuserGroupForm(data=form_data)
        ok_(form.is_valid())

    def test_required_criteria(self):
        form_data = {'name': 'test group', 'accepting_new_members': 'by_request'}
        form = SuperuserGroupForm(data=form_data)
        eq_(False, form.is_valid())
        ok_('new_member_criteria' in form.errors)

        form_data = {'name': 'test group', 'accepting_new_members': 'by_request', 'new_member_criteria': 'some criteria'}
        form = SuperuserGroupForm(data=form_data)
        ok_(form.is_valid())
        ok_('new_member_criteria' in form.cleaned_data)

    def test_no_saved_criteria(self):
        form_data = {'name': 'test group', 'accepting_new_members': 'no', 'new_member_criteria': 'some criteria'}
        form = SuperuserGroupForm(data=form_data)
        ok_(form.is_valid())
        eq_(u'', form.cleaned_data['new_member_criteria'])

        form_data = {'name': 'test group', 'accepting_new_members': 'yes', 'new_member_criteria': 'some criteria'}
        form = SuperuserGroupForm(data=form_data)
        ok_(form.is_valid())
        eq_(u'', form.cleaned_data['new_member_criteria'])
