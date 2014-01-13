# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse

from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.groups.models import Group, GroupAlias, GroupMembership
from mozillians.groups.tests import GroupAliasFactory, GroupFactory, \
    SkillFactory
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

    def test_add_member(self):
        skill = SkillFactory.create()
        user = UserFactory.create()
        ok_(user.userprofile not in skill.members.all())
        skill.add_member(userprofile=user.userprofile)
        ok_(user.userprofile in skill.members.all())
        ok_(skill.has_member(userprofile=user.userprofile))

    def test_remove_member(self):
        skill = SkillFactory.create()
        user = UserFactory.create()
        skill.members.add(user.userprofile)
        skill.remove_member(userprofile=user.userprofile)
        ok_(not skill.has_member(userprofile=user.userprofile))
        ok_(user.userprofile not in skill.members.all())

    def test_has_member(self):
        skill = SkillFactory.create()
        user = UserFactory.create()
        ok_(not skill.has_member(userprofile=user.userprofile))
        skill.members.add(user.userprofile)
        ok_(skill.has_member(userprofile=user.userprofile))


class GroupTests(TestCase):
    def test_get_non_functional_areas(self):
        UserFactory.create()
        UserFactory.create()
        GroupFactory.create(functional_area=True)
        cgroup_2 = GroupFactory.create(functional_area=False)
        eq_(set(Group.get_non_functional_areas()), set([cgroup_2]))

    def test_get_functional_areas(self):
        GroupFactory.create()
        GroupFactory.create()
        UserFactory.create()
        UserFactory.create()
        cgroup_1 = GroupFactory.create(functional_area=True)
        GroupFactory.create(functional_area=False)
        eq_(set(Group.get_functional_areas()), set([cgroup_1]))

    def test_deleted_curator_sets_null(self):
        user = UserFactory.create()
        group = GroupFactory.create(curator=user.userprofile)

        user.delete()
        group = Group.objects.get(id=group.id)
        eq_(group.curator, None)

    def test_remove_member(self):
        user = UserFactory.create()
        group = GroupFactory.create()
        GroupMembership.objects.create(userprofile=user.userprofile, group=group,
                                       status=GroupMembership.MEMBER)
        ok_(group.has_member(user.userprofile))

        group.remove_member(user.userprofile)
        ok_(not GroupMembership.objects.filter(userprofile=user.userprofile, group=group).exists())
        ok_(not group.has_member(user.userprofile))

    def test_add_member(self):
        user = UserFactory.create()
        group = GroupFactory.create()
        ok_(not group.has_member(user.userprofile))
        group.add_member(user.userprofile)
        ok_(GroupMembership.objects.filter(userprofile=user.userprofile, group=group,
                                           status=GroupMembership.MEMBER).exists())
        ok_(group.has_member(user.userprofile))
        group.add_member(user.userprofile, status=GroupMembership.PENDING)
        ok_(GroupMembership.objects.filter(userprofile=user.userprofile, group=group,
                                           status=GroupMembership.PENDING).exists())
        ok_(not group.has_member(user.userprofile))
        ok_(group.has_pending_member(user.userprofile))

    def test_has_member(self):
        user = UserFactory.create()
        group = GroupFactory.create()
        ok_(not group.has_member(user.userprofile))
        GroupMembership.objects.create(userprofile=user.userprofile, group=group,
                                       status=GroupMembership.MEMBER)
        ok_(group.has_member(user.userprofile))
        group.remove_member(user.userprofile)
        ok_(not group.has_member(user.userprofile))


class GroupAliasBaseTests(TestCase):
    def test_auto_slug_field(self):
        group = GroupFactory.create()
        group_alias = group.aliases.all()[0]
        ok_(group_alias.url)

    def test_slug_uniqueness(self):
        group_1 = GroupFactory.create(name='foo-1')
        group_2 = GroupFactory.create(name='foo 1')
        ok_(group_1.url != group_2.url)

    def test_auto_slug_field_urlness(self):
        # The auto slug field comes up with a string that our group URLs will match
        group = GroupFactory.create(name=u'A (ñâme)-with_"s0me" \'screwy\' chars')
        reverse('groups:show_group', args=[group.url])

    def test_auto_slug_field_unicode(self):
        # The auto slug field dumbs down unicode into ASCII rather than just
        # throwing it away
        group = GroupFactory.create(name=u'A (ñâme)-with_ελλάδα "s0me" \'screwy\' chars')
        eq_(u'a-name-with_ellada-s0me-screwy-chars', group.url)
