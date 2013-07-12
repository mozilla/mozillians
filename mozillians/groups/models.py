from django.db import models

from autoslug.fields import AutoSlugField
from tower import ugettext_lazy as _lazy


# If three or more users use a group, it will get auto-completed.
AUTO_COMPLETE_COUNT = 3


class GroupBase(models.Model):
    name = models.CharField(db_index=True, max_length=50, unique=True)
    url = models.SlugField(blank=True)

    # If this is true, this Group/Skill/Language will appear in the
    # autocomplete list.
    auto_complete = models.BooleanField(db_index=True, default=False)
    always_auto_complete = models.BooleanField(default=False)

    class Meta:
        abstract = True
        ordering = ['name']


    @classmethod
    def search(cls, query, auto_complete_only=True):
        if not query:
            return []
        query = query.lower()
        results = cls.objects.filter(name__contains=query)
        if auto_complete_only:
            results = results.filter(auto_complete=auto_complete_only)
        return results

    def save(self, *args, **kwargs):
        self.name = self.name.lower()
        super(GroupBase, self).save()
        if not self.url:
            alias = self.ALIAS_MODEL.objects.create(name=self.name, alias=self)
            self.url = alias.url
            super(GroupBase, self).save()

    def __unicode__(self):
        return self.name

    def merge_groups(self, group_list):
        for group in group_list:
            map(lambda x: self.members.add(x),
                group.members.values_list('id', flat=True))
            group.aliases.update(alias=self)
            group.delete()


class GroupAliasBase(models.Model):
    name = models.CharField(max_length=50, unique=True)
    url = AutoSlugField(populate_from='name', unique=True,
                        editable=False, blank=True)

    class Meta:
        abstract = True


class GroupAlias(GroupAliasBase):
    alias = models.ForeignKey('Group', related_name='aliases')


class Group(GroupBase):
    ALIAS_MODEL = GroupAlias

    system = models.BooleanField(db_index=True, default=False)
    # Has a steward taken ownership of this group?
    description = models.TextField(max_length=255,
            verbose_name=_lazy(u'Description'), default='', blank=True)
    steward = models.ForeignKey('users.UserProfile',
            blank=True, null=True, on_delete=models.SET_NULL)
    irc_channel = models.CharField(max_length=63,
            verbose_name=_lazy(u'IRC Channel'), default='', blank=True)
    website = models.URLField(max_length=200, verbose_name=_lazy(u'Website'),
            default='', blank=True)
    wiki = models.URLField(max_length=200, verbose_name=_lazy(u'Wiki'),
            default='', blank=True)

    @classmethod
    def get_curated(cls):
        """Return all the groups with a steward assigned."""
        return cls.objects.exclude(steward=None).annotate(
            num_members=models.Count('members'))

    class Meta:
        db_table = 'group'



class SkillAlias(GroupAliasBase):
    alias = models.ForeignKey('Skill', related_name='aliases')

    class Meta:
        verbose_name_plural = 'skill aliases'


class Skill(GroupBase):
    ALIAS_MODEL = SkillAlias


class LanguageAlias(GroupAliasBase):
    alias = models.ForeignKey('Language', related_name='aliases')

    class Meta:
        verbose_name_plural = 'language aliases'

class Language(GroupBase):
    ALIAS_MODEL = LanguageAlias
