from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from autoslug.fields import AutoSlugField
from tower import ugettext_lazy as _lazy

# If three or more users use a group, it will get auto-completed.
AUTO_COMPLETE_COUNT = 3


class GroupBase(models.Model):
    """Base model for Languages, Skills and Groups.

    Think of tags on a user profile.
    """
    name = models.CharField(db_index=True, max_length=50, unique=True)
    url = models.SlugField(blank=True)

    # If this is true, this Group/Skill/Language will appear in the
    # autocomplete list.
    auto_complete = models.BooleanField(db_index=True, default=False)
    always_auto_complete = models.BooleanField(default=False)

    class Meta:
        abstract = True

    @classmethod
    def search(cls, query, auto_complete_only=True):
        if query:
            return cls.objects.filter(name__icontains=query,
                                      auto_complete=auto_complete_only)
        return []

    def __unicode__(self):
        """Return the name of this group, unless it doesn't have one
        yet.

        """
        return self.name


class GroupAliasBase(models.Model):
    name = models.CharField(max_length=50, unique=True)
    url = AutoSlugField(populate_from='name', unique=True,
                        editable=False, blank=True)

    class Meta:
        abstract = True


class Group(GroupBase):
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

    def save(self, *args, **kwargs):
        self.name = self.name.lower()
        super(Group, self).save()
        if not self.url:
            alias = GroupAlias.objects.create(name=self.name, alias=self)
            self.url = alias.url
            super(Group, self).save()


class GroupAlias(GroupAliasBase):
    alias = models.ForeignKey(Group, related_name='aliases')

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name_plural = 'group aliases'


class Skill(GroupBase):
    """Model to hold skill tags.

    Like groups but with less attributes.

    """
    def save(self, *args, **kwargs):
        self.name = self.name.lower()
        super(Skill, self).save()
        if not self.url:
            alias = SkillAlias.objects.create(name=self.name, alias=self)
            self.url = alias.url
            super(Skill, self).save()


class SkillAlias(GroupAliasBase):
    alias = models.ForeignKey(Skill, related_name='aliases')

    class Meta:
        verbose_name_plural = 'skill aliases'


class Language(GroupBase):
    """Model to hold languages spoken tags.

    Like groups but with less attributes.
    """
    def save(self, *args, **kwargs):
        self.name = self.name.lower()
        super(Language, self).save()
        if not self.url:
            alias = LanguageAlias.objects.create(name=self.name, alias=self)
            self.url = alias.url
            super(Language, self).save()


class LanguageAlias(GroupAliasBase):
    alias = models.ForeignKey(Language, related_name='aliases')

    class Meta:
        verbose_name_plural = 'language aliases'
