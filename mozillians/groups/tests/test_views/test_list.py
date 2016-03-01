from django.test import RequestFactory

from mock import patch
from nose.tools import ok_, eq_

from mozillians.common.tests import TestCase
from mozillians.groups.models import Group
from mozillians.groups.tests import GroupFactory
from mozillians.groups.views import _list_groups
from mozillians.users.tests import UserFactory


@patch('mozillians.groups.views.settings.ITEMS_PER_PAGE', 1)
@patch('mozillians.groups.views.render')
class ListTests(TestCase):
    def setUp(self):
        self.user = UserFactory.create()
        self.group_1 = GroupFactory.create(name='abc')
        self.group_2 = GroupFactory.create(name='def')
        self.group_2.add_member(self.user.userprofile)
        self.query = Group.objects.filter(pk__in=[self.group_1.pk, self.group_2.pk])
        self.template = 'groups/index.html'
        self.request = RequestFactory()
        self.request.GET = {}
        self.request.user = self.user

    def test_list_groups(self, render_mock):
        _list_groups(self.request, self.template, self.query)
        ok_(render_mock.called)
        request, template, data = render_mock.call_args[0]
        eq_(template, self.template)
        eq_(data['groups'].paginator.count, 2)
        eq_(data['groups'].paginator.num_pages, 2)
        eq_(data['groups'].number, 1)
        eq_(data['groups'].object_list[0], self.group_1)

    def test_sort_by_name(self, render_mock):
        self.request.GET = {'sort': 'name'}
        _list_groups(self.request, self.template, self.query)
        ok_(render_mock.called)
        request, template, data = render_mock.call_args[0]
        eq_(data['groups'].object_list[0], self.group_1)

    def test_sort_by_most_members(self, render_mock):
        self.request.GET = {'sort': '-member_count'}
        _list_groups(self.request, self.template, self.query)
        ok_(render_mock.called)
        request, template, data = render_mock.call_args[0]
        eq_(data['groups'].object_list[0], self.group_2)

    def test_sort_by_fewest_members(self, render_mock):
        self.request.GET = {'sort': 'member_count'}
        _list_groups(self.request, self.template, self.query)
        ok_(render_mock.called)
        request, template, data = render_mock.call_args[0]
        eq_(data['groups'].object_list[0], self.group_1)

    def test_invalid_sort(self, render_mock):
        self.request.GET = {'sort': 'invalid'}
        _list_groups(self.request, self.template, self.query)
        ok_(render_mock.called)
        request, template, data = render_mock.call_args[0]
        eq_(data['groups'].object_list[0], self.group_1)

    def test_second_page(self, render_mock):
        self.request.GET = {'page': '2'}
        _list_groups(self.request, self.template, self.query)
        ok_(render_mock.called)
        request, template, data = render_mock.call_args[0]
        eq_(data['groups'].number, 2)

    def test_empty_page(self, render_mock):
        self.request.GET = {'page': '20000'}
        _list_groups(self.request, self.template, self.query)
        ok_(render_mock.called)
        request, template, data = render_mock.call_args[0]
        eq_(data['groups'].number, 2)

    def test_invalid_page(self, render_mock):
        self.request.GET = {'page': 'invalid'}
        _list_groups(self.request, self.template, self.query)
        ok_(render_mock.called)
        request, template, data = render_mock.call_args[0]
        eq_(data['groups'].number, 1)
