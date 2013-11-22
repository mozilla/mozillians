# -*- coding: utf-8 -*-
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.groups.models import Group, GroupAlias
from mozillians.groups.tests import GroupAliasFactory, GroupFactory
from mozillians.users.tests import UserFactory


class GroupBaseTests(TestCase):
    def test_groups_are_saved_lowercase(self):
        group = GroupFactory.create(name='FooBAR')
        eq_(group.name, 'foobar')

    def test_group_has_alias(self):
        group = GroupFactory.create()
        ok_(GroupAlias.objects.get(alias=group))

    def test_group_has_url(self):
        group = GroupFactory.create()
        ok_(group.url)

    def test_merge_groups(self):
        master_group = GroupFactory.create()
        merge_group_1 = GroupFactory.create()
        merge_group_2 = GroupFactory.create()
        nested_group = GroupFactory.create()
        merge_group_1.merge_groups([nested_group])
        master_group.merge_groups([merge_group_1, merge_group_2])
        eq_(master_group.aliases.count(), 4)
        for group in [merge_group_1, merge_group_2, nested_group]:
            ok_(master_group.aliases.filter(name=group.name,
                                            url=group.url).exists())
            ok_(not Group.objects.filter(pk=group.pk).exists())

    def test_search(self):
        group = GroupFactory.create(visible=True)
        GroupFactory.create(visible=False)

        eq_(set(Group.search(group.name)), set([group]))
        eq_(set(Group.search('roup'.format(group.name))), set([group]))

    def test_search_case_insensitive(self):
        group = GroupFactory.create(visible=True)
        query = 'GROUP'
        eq_(set(Group.search(query)), set([group]))

    def test_search_no_query(self):
        eq_(len(Group.search('invalid')), 0)

    def test_search_matches_alias(self):
        group_1 = GroupFactory.create(name='lalo', visible=True)
        GroupAliasFactory.create(alias=group_1, name='foo')
        eq_(set(Group.search('foo')), set([group_1]))

    def test_search_distict_results(self):
        group_1 = GroupFactory.create(name='automation', visible=True)
        GroupAliasFactory.create(alias=group_1, name='automation development')
        GroupAliasFactory.create(alias=group_1, name='automation services')
        results = Group.search('automation')
        eq_(len(results), 1)
        eq_(results[0], group_1)


class GroupTests(TestCase):
    def test_get_non_functional_areas(self):
        user_1 = UserFactory.create()
        user_2 = UserFactory.create()
        cgroup_1 = GroupFactory.create(functional_area=True)
        cgroup_2 = GroupFactory.create(functional_area=False)
        eq_(set(Group.get_non_functional_areas()), set([cgroup_2]))

    def test_get_functional_areas(self):
        GroupFactory.create()
        GroupFactory.create()
        user_1 = UserFactory.create()
        user_2 = UserFactory.create()
        cgroup_1 = GroupFactory.create(functional_area=True)
        cgroup_2 = GroupFactory.create(functional_area=False)
        eq_(set(Group.get_functional_areas()), set([cgroup_1]))

    def test_deleted_curator_sets_null(self):
        user = UserFactory.create()
        group = GroupFactory.create(curator=user.userprofile)

        user.delete()
        group = Group.objects.get(id=group.id)
        eq_(group.curator, None)


class GroupAliasBaseTests(TestCase):
    def test_auto_slug_field(self):
        group = GroupFactory.create()
        group_alias = group.aliases.all()[0]
        ok_(group_alias.url)

    def test_slug_uniqueness(self):
        group_1 = GroupFactory.create(name='foo-1')
        group_2 = GroupFactory.create(name='foo 1')
        ok_(group_1.url != group_2.url)
