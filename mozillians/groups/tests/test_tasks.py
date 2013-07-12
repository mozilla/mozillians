from mock import patch
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase, UserFactory
from mozillians.groups import tasks
from mozillians.groups.models import Group, Skill
from mozillians.groups.tests import GroupFactory, SkillFactory


class TaskTests(TestCase):
    @patch('mozillians.groups.tasks.AUTO_COMPLETE_COUNT', 1)
    def test_autocomplete_assign(self):
        user = UserFactory.create()
        group_1 = GroupFactory.create()
        group_2 = GroupFactory.create(auto_complete=False)
        group_1.members.add(user.userprofile)
        tasks.assign_autocomplete_to_groups()
        group_1 = Group.objects.get(pk=group_1.pk)
        group_2 = Group.objects.get(pk=group_2.pk)
        eq_(group_1.auto_complete, True)
        eq_(group_2.auto_complete, False)

    def test_remove_empty_groups(self):
        user = UserFactory.create()
        group_1 = GroupFactory.create()
        GroupFactory.create()
        skill_1 = SkillFactory.create()
        SkillFactory.create()

        group_1.members.add(user.userprofile)
        skill_1.members.add(user.userprofile)

        tasks.remove_empty_groups()

        eq_(Group.objects.all().count(), 1)
        ok_(Group.objects.filter(id=group_1.id).exists())
        eq_(Skill.objects.all().count(), 1)
        ok_(Skill.objects.filter(id=skill_1.id).exists())
