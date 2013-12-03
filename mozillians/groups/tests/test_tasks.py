from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.groups import tasks
from mozillians.groups.models import Group, Skill
from mozillians.groups.tests import GroupFactory, SkillFactory
from mozillians.users.tests import UserFactory


class TaskTests(TestCase):

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
