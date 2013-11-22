from django.db import models

from autoslug.fields import AutoSlugField
from tower import ugettext_lazy as _lazy


class GroupBase(models.Model):
    name = models.CharField(db_index=True, max_length=50, unique=True)
    url = models.SlugField(blank=True)

    class Meta:
        abstract = True
        ordering = ['name']

    @classmethod
    def search(cls, query):
        if not query:
            return []
        query = query.lower()
        results = cls.objects.filter(aliases__name__contains=query)
        results = results.distinct()
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

    def user_can_leave(self, user):
        return (
            # some groups don't allow leaving
            getattr(self, 'members_can_leave', True)
            and
            # curators cannot leave their own groups
            getattr(self, 'curator', None) != user.userprofile
            and
            # can only leave a group they belong to
            self.members.filter(user=user).exists()
        )

    def user_can_join(self, user):
        return (
            # some groups don't allow
            getattr(self, 'accepting_new_members', 'yes') != 'no'
            and
            # can only join if not already a member
            not self.members.filter(user=user).exists()
        )

    # Read-only properties so clients don't care which subclasses have some fields
    @property
    def is_visible(self):
        return getattr(self, 'visible', True)


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

    # Has a steward taken ownership of this group?
    description = models.TextField(max_length=255,
                                   verbose_name=_lazy(u'Description'),
                                   default='', blank=True)
    curator = models.ForeignKey('users.UserProfile',
                                blank=True, null=True,
                                on_delete=models.SET_NULL,
                                related_name='groups_curated')
    irc_channel = models.CharField(max_length=63,
                                   verbose_name=_lazy(u'IRC Channel'),
                                   default='', blank=True)
    website = models.URLField(max_length=200, verbose_name=_lazy(u'Website'),
                              default='', blank=True)
    wiki = models.URLField(max_length=200, verbose_name=_lazy(u'Wiki'),
                           default='', blank=True)
    members_can_leave = models.BooleanField(default=True)
    accepting_new_members = models.CharField(
        choices=(
            ("yes", _lazy(u"Yes")),
            ("by_request", _lazy(u"By request")),
            ("no", _lazy(u"No")),
        ),
        default="by_request",
        max_length=10
    )
    functional_area = models.BooleanField(default=False)
    visible = models.BooleanField(
        default=True,
        help_text="Whether group is shown on the UI (in group lists, search, etc). Mainly intended to keep system groups like 'staff' from cluttering up the interface."
    )

    @classmethod
    def get_functional_areas(cls):
        """Return all visible groups that are functional areas."""
        return cls.objects.filter(functional_area=True, visible=True).annotate(
            num_members=models.Count('members'))

    @classmethod
    def get_non_functional_areas(cls):
        """Return all visible groups that are not functional areas."""
        return cls.objects.filter(functional_area=False, visible=True).annotate(
            num_members=models.Count('members'))

    @classmethod
    def get_curated(cls):
        """Return all non-functional areas that are curated."""
        return cls.get_non_functional_areas().filter(curator__isnull=False)

    @classmethod
    def search(cls, query):
        results = super(Group, cls).search(query)
        results = results.filter(visible=True)
        return results


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
