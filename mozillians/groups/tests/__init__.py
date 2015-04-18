import factory

from mozillians.groups.models import Group, GroupAlias, Skill, SkillAlias


class GroupFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Group {0}'.format(n))

    class Meta:
        model = Group


class SkillFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Skill {0}'.format(n))

    class Meta:
        model = Skill


class GroupAliasFactory(factory.DjangoModelFactory):
    url = factory.Sequence(lambda n: 'alias-{0}'.format(n))

    class Meta:
        model = GroupAlias


class SkillAliasFactory(factory.DjangoModelFactory):
    url = factory.Sequence(lambda n: 'alias-{0}'.format(n))

    class Meta:
        model = SkillAlias
