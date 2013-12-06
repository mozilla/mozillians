from django.db import models
from django.db.models import Q
from django.utils.timezone import now

from autoslug.fields import AutoSlugField
from funfactory.urlresolvers import reverse
from funfactory.utils import absolutify
from tower import ugettext_lazy as _lazy

from mozillians.groups.helpers import slugify
from mozillians.groups.tasks import email_membership_change
from mozillians.users.tasks import update_basket_task


class GroupBase(models.Model):
    name = models.CharField(db_index=True, max_length=50, unique=True)
    url = models.SlugField(blank=True)

    class Meta:
        abstract = True
        ordering = ['name']

    @classmethod
    def search(cls, query):
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
            map(lambda x: self.add_member(x),
                group.members.values_list('id', flat=True))
            group.aliases.update(alias=self)
            group.delete()

    def user_can_leave(self, userprofile):
        return (
            # some groups don't allow leaving
            getattr(self, 'members_can_leave', True)
            and
            # curators cannot leave their own groups
            getattr(self, 'curator', None) != userprofile
            and
            # only makes sense to leave a group they belong to (at least pending)
            (self.has_member(userprofile=userprofile)
             or self.has_pending_member(userprofile=userprofile))
        )

    def user_can_join(self, userprofile):
        return (
            # some groups don't allow
            (getattr(self, 'accepting_new_members', 'yes') != 'no')
            and
            # only makes sense to join if not already a member (full or pending)
            not (self.has_member(userprofile=userprofile)
                 or self.has_pending_member(userprofile=userprofile))
        )

    # Read-only properties so clients don't care which subclasses have some fields
    @property
    def is_visible(self):
        return getattr(self, 'visible', True)

    def add_member(self, userprofile):
        self.members.add(userprofile)
        update_basket_task.delay(userprofile.id)

    def remove_member(self, userprofile):
        self.members.remove(userprofile)
        update_basket_task.delay(userprofile.id)

    def has_member(self, userprofile):
        return self.members.filter(user=userprofile.user).exists()

    def has_pending_member(self, userprofile):
        # skills and languages have no pending members, just members
        return False


class GroupAliasBase(models.Model):
    name = models.CharField(max_length=50, unique=True)
    url = AutoSlugField(populate_from='name', unique=True,
                        editable=False, blank=True,
                        slugify=slugify)

    class Meta:
        abstract = True


class GroupAlias(GroupAliasBase):
    alias = models.ForeignKey('Group', related_name='aliases')


class GroupMembership(models.Model):
    """
    Through model for UserProfile <-> Group relationship
    """
    # Possible membership statuses:
    MEMBER = u'member'
    PENDING = u'pending'  # Has requested to join group, not a member yet

    MEMBERSHIP_STATUS_CHOICES = (
        (MEMBER, _lazy(u'Member')),
        (PENDING, _lazy(u'Pending')),
    )

    userprofile = models.ForeignKey('users.UserProfile', db_index=True)
    group = models.ForeignKey('groups.Group', db_index=True)
    status = models.CharField(choices=MEMBERSHIP_STATUS_CHOICES, max_length=10)
    date_joined = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('userprofile', 'group')

    def __unicode__(self):
        return u'%s in %s' % (self.userprofile, self.group)


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
    irc_channel = models.CharField(
        max_length=63,
        verbose_name=_lazy(u'IRC Channel'),
        help_text=_lazy(u'An IRC channel where this group is discussed (optional).'),
        default='', blank=True)
    website = models.URLField(
        max_length=200, verbose_name=_lazy(u'Website'),
        help_text=_lazy(u'A URL of a web site with more information about this group (optional).'),
        default='', blank=True)
    wiki = models.URLField(
        max_length=200, verbose_name=_lazy(u'Wiki'),
        help_text=_lazy(u'A URL of a wiki with more information about this group (optional).'),
        default='', blank=True)
    members_can_leave = models.BooleanField(default=True)
    accepting_new_members = models.CharField(
        choices=(
            ('yes', _lazy(u'Yes')),
            ('by_request', _lazy(u'By request')),
            ('no', _lazy(u'No')),
        ),
        default='by_request',
        max_length=10
    )
    functional_area = models.BooleanField(default=False)
    visible = models.BooleanField(
        default=True,
        help_text=_lazy(u'Whether group is shown on the UI (in group lists, search, etc). Mainly '
                        u'intended to keep system groups like "staff" from cluttering up the '
                        u'interface.')
    )
    max_reminder = models.IntegerField(
        default=0,
        help_text=_lazy(u'The max PK of pending membership requests the last time we sent the '
                        u'curator a reminder')
    )

    @classmethod
    def get_functional_areas(cls):
        """Return all visible groups that are functional areas."""
        return cls.objects.filter(functional_area=True, visible=True).annotate(
            num_members=models.Count('members'))

    @classmethod
    def get_non_functional_areas(cls, **kwargs):
        """
        Return all visible groups that are not functional areas.

        Use kwargs to apply additional filtering to the groups.
        """
        return cls.objects.filter(functional_area=False, visible=True, **kwargs).annotate(
            num_members=models.Count('members'))

    @classmethod
    def get_curated(cls):
        """Return all non-functional areas that are curated."""
        return cls.get_non_functional_areas(curator__isnull=False)

    @classmethod
    def search(cls, query):
        results = super(Group, cls).search(query)
        results = results.filter(visible=True)
        return results

    def get_absolute_url(self):
        return absolutify(reverse('groups:show_group', args=[self.url]))

    def add_member(self, userprofile, status=GroupMembership.MEMBER):
        """
        Add a user to this group. Optionally specify status other than member.

        If user is already in the group with the given status, this is a no-op.

        If user is already in the group with a different status, their status will
        be updated.
        """
        defaults = dict(status=status,
                        date_joined=now())
        membership, created = GroupMembership.objects.get_or_create(userprofile=userprofile,
                                                                    group=self,
                                                                    defaults=defaults)
        if created:
            if status == GroupMembership.MEMBER:
                # Joined
                update_basket_task.delay(userprofile.id)
        elif not created and membership.status != status:
            # Status changed
            old_status = membership.status
            membership.status = status
            membership.save()
            update_basket_task.delay(userprofile.id)
            if (old_status, status) == (GroupMembership.PENDING, GroupMembership.MEMBER):
                # Request accepted
                email_membership_change.delay(self.pk, userprofile.user.pk, old_status, status)

    def remove_member(self, userprofile, send_email=True):
        membership = GroupMembership.objects.get(group=self, userprofile=userprofile)
        old_status = membership.status
        membership.delete()
        update_basket_task.delay(userprofile.id)
        if old_status == GroupMembership.PENDING and send_email:
            # Request denied
            email_membership_change.delay(self.pk, userprofile.user.pk,
                                          old_status, None)

    def has_member(self, userprofile):
        """
        Return True if this user is in this group with status MEMBER.
        """
        return GroupMembership.objects.filter(group=self, userprofile=userprofile,
                                              status=GroupMembership.MEMBER).exists()

    def has_pending_member(self, userprofile):
        """
        Return True if this user is in this group with status PENDING.
        """
        return GroupMembership.objects.filter(group=self, userprofile=userprofile,
                                              status=GroupMembership.PENDING).exists()

    def get_vouched_annotated_members(self, statuses=None, always_include=None):
        """
        Return list of UserProfiles of vouched users who are members or pending members.

        Pass ``statuses`` a list of desired statuses to filter by status too.

        Pass a userprofile in ``always_include`` to include that userprofile regardless
        of status (so we show a user that they are in the group in pending state).

        Attribute ``.pending`` indicates whether membership is only pending.
        Attribute ``.is_curator`` indicates if member is a curator of this group
        """
        memberships = GroupMembership.objects.filter(group=self,
                                                     userprofile__is_vouched=True)
        if statuses is not None:
            if always_include is not None:
                memberships = memberships.filter(Q(status__in=statuses)
                                                 | Q(userprofile=always_include))
            else:
                memberships = memberships.filter(status__in=statuses)
        profiles = []
        for membership in memberships:
            profile = membership.userprofile
            profile.pending = (membership.status == GroupMembership.PENDING)
            profile.is_curator = (self.curator == profile)
            profiles.append(profile)
        return profiles


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
