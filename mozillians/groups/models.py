from django.core.exceptions import ValidationError
from django.db import models
from django.utils.timezone import now

from autoslug.fields import AutoSlugField
from funfactory.urlresolvers import reverse
from funfactory.utils import absolutify
from tower import ugettext as _
from tower import ugettext_lazy as _lazy

from mozillians.groups.managers import GroupBaseManager, GroupQuerySet
from mozillians.groups.helpers import slugify
from mozillians.groups.tasks import email_membership_change, member_removed_email
from mozillians.users.tasks import update_basket_task


class GroupBase(models.Model):
    name = models.CharField(db_index=True, max_length=50,
                            unique=True, verbose_name=_lazy(u'Name'))
    url = models.SlugField(blank=True)

    objects = GroupBaseManager.from_queryset(GroupQuerySet)()

    class Meta:
        abstract = True
        ordering = ['name']

    def clean(self):
        """Verify that name is unique in ALIAS_MODEL."""

        super(GroupBase, self).clean()
        query = self.ALIAS_MODEL.objects.filter(name=self.name)
        if self.pk:
            query = query.exclude(alias=self)
        if query.exists():
            raise ValidationError({'name': _('This name already exists.')})
        return self.name

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
                group.members.all())
            group.aliases.update(alias=self)
            group.delete()

    def user_can_leave(self, userprofile):
        curators = self.curators.all()
        return (
            # some groups don't allow leaving
            getattr(self, 'members_can_leave', True) and
            # We need at least one curator
            (curators.count() > 1 or userprofile not in curators) and
            # only makes sense to leave a group they belong to (at least pending)
            (self.has_member(userprofile=userprofile) or
                self.has_pending_member(userprofile=userprofile))
        )

    def user_can_join(self, userprofile):
        return (
            # Must be vouched
            userprofile.is_vouched and
            # some groups don't allow
            (getattr(self, 'accepting_new_members', 'yes') != 'no') and
            # only makes sense to join if not already a member (full or pending)
            not (self.has_member(userprofile=userprofile) or
                 self.has_pending_member(userprofile=userprofile))
        )

    # Read-only properties so clients don't care which subclasses have some fields
    @property
    def is_visible(self):
        return getattr(self, 'visible', True)

    def add_member(self, userprofile):
        self.members.add(userprofile)

    def remove_member(self, userprofile):
        self.members.remove(userprofile)

    def has_member(self, userprofile):
        return self.members.filter(user=userprofile.user).exists()

    def has_pending_member(self, userprofile):
        # skills have no pending members, just members
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
    PENDING_TERMS = u'pending_terms'

    MEMBERSHIP_STATUS_CHOICES = (
        (MEMBER, _lazy(u'Member')),
        (PENDING_TERMS, _lazy(u'Pending terms')),
        (PENDING, _lazy(u'Pending')),
    )

    userprofile = models.ForeignKey('users.UserProfile', db_index=True)
    group = models.ForeignKey('groups.Group', db_index=True)
    status = models.CharField(choices=MEMBERSHIP_STATUS_CHOICES, max_length=15)
    date_joined = models.DateTimeField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        unique_together = ('userprofile', 'group')

    def __unicode__(self):
        return u'%s in %s' % (self.userprofile, self.group)


class Group(GroupBase):
    ALIAS_MODEL = GroupAlias

    # Has a steward taken ownership of this group?
    description = models.TextField(max_length=1024,
                                   verbose_name=_lazy(u'Description'),
                                   default='', blank=True)
    curators = models.ManyToManyField('users.UserProfile',
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
        verbose_name=_lazy(u'Accepting new members'),
        choices=(
            ('yes', _lazy(u'Yes')),
            ('by_request', _lazy(u'By request')),
            ('no', _lazy(u'No')),
        ),
        default='yes',
        max_length=10
    )
    new_member_criteria = models.TextField(
        max_length=1024,
        default='',
        blank=True,
        verbose_name=_lazy(u'New Member Criteria'),
        help_text=_lazy(u'Specify the criteria you will use to decide whether or not '
                        u'you will accept a membership request.'))
    functional_area = models.BooleanField(default=False)
    visible = models.BooleanField(
        default=True,
        help_text=_lazy(u'Whether group is shown on the UI (in group lists, search, etc). Mainly '
                        u'intended to keep system groups like "staff" from cluttering up the '
                        u'interface.')
    )
    max_reminder = models.IntegerField(
        default=0,
        help_text=(u'The max PK of pending membership requests the last time we sent the '
                   u'curator a reminder')
    )

    terms = models.TextField(default='', verbose_name=_('Terms'), blank=True)
    invalidation_days = models.PositiveIntegerField(null=True, default=None, blank=True,
                                                    verbose_name=_('Invalidation days'))
    objects = GroupBaseManager.from_queryset(GroupQuerySet)()

    @classmethod
    def get_functional_areas(cls):
        """Return all visible groups that are functional areas."""
        return cls.objects.visible().filter(functional_area=True)

    @classmethod
    def get_non_functional_areas(cls, **kwargs):
        """
        Return all visible groups that are not functional areas.

        Use kwargs to apply additional filtering to the groups.
        """
        return cls.objects.visible().filter(functional_area=False, **kwargs)

    @classmethod
    def get_curated(cls):
        """Return all non-functional areas that are curated."""
        return cls.get_non_functional_areas(curators__isnull=False)

    @classmethod
    def search(cls, query):
        return super(Group, cls).search(query).visible()

    def get_absolute_url(self):
        return absolutify(reverse('groups:show_group', args=[self.url]))

    def merge_groups(self, group_list):
        for membership in GroupMembership.objects.filter(group__in=group_list):
            # add_member will never demote someone, so just add them with the current membership
            # level from the merging group and they'll end up with the highest level from
            # either group.
            self.add_member(membership.userprofile, membership.status)

        for group in group_list:
            group.aliases.update(alias=self)
            group.delete()

    def add_member(self, userprofile, status=GroupMembership.MEMBER):
        """
        Add a user to this group. Optionally specify status other than member.

        If user is already in the group with the given status, this is a no-op.

        If user is already in the group with a different status, their status will
        be updated if the change is a promotion. Otherwise, their status will not change.
        """
        defaults = dict(status=status,
                        date_joined=now())
        membership, created = GroupMembership.objects.get_or_create(userprofile=userprofile,
                                                                    group=self,
                                                                    defaults=defaults)
        if created:
            if status == GroupMembership.MEMBER:
                # Joined
                # Group is functional area, we want to sent this update to Basket
                if self.functional_area:
                    update_basket_task.delay(userprofile.id)
        else:
            if membership.status != status:
                # Status changed
                # The only valid status change states are:
                # PENDING to MEMBER
                # PENDING to PENDING_TERMS
                # PENDING_TERMS to MEMBER

                old_status = membership.status
                membership.status = status
                statuses = [(GroupMembership.PENDING, GroupMembership.MEMBER),
                            (GroupMembership.PENDING, GroupMembership.PENDING_TERMS),
                            (GroupMembership.PENDING_TERMS, GroupMembership.MEMBER)]
                if (old_status, status) in statuses:
                    # Status changed
                    membership.save()
                    if membership.status in [GroupMembership.PENDING, GroupMembership.MEMBER]:
                        if self.functional_area:
                            # Group is functional area, we want to sent this update to Basket.
                            update_basket_task.delay(userprofile.id)
                        email_membership_change.delay(self.pk, userprofile.user.pk,
                                                      old_status, status)

    def remove_member(self, userprofile, send_email=True):
        try:
            membership = GroupMembership.objects.get(group=self, userprofile=userprofile)
        except GroupMembership.DoesNotExist:
            return
        old_status = membership.status
        membership.delete()
        # If group is functional area, we want to sent this update to Basket
        if self.functional_area:
            update_basket_task.delay(userprofile.id)

        if old_status == GroupMembership.PENDING and send_email:
            # Request denied
            email_membership_change.delay(self.pk, userprofile.user.pk,
                                          old_status, None)
        elif old_status == GroupMembership.MEMBER and send_email:
            # Member removed
            member_removed_email.delay(self.pk, userprofile.user.pk)

    def has_member(self, userprofile):
        """
        Return True if this user is in this group with status MEMBER.
        """
        return self.groupmembership_set.filter(userprofile=userprofile,
                                               status=GroupMembership.MEMBER).exists()

    def has_pending_member(self, userprofile):
        """
        Return True if this user is in this group with status PENDING.
        """
        return self.groupmembership_set.filter(userprofile=userprofile,
                                               status=GroupMembership.PENDING).exists()


class SkillAlias(GroupAliasBase):
    alias = models.ForeignKey('Skill', related_name='aliases')

    class Meta:
        verbose_name_plural = 'skill aliases'


class Skill(GroupBase):
    ALIAS_MODEL = SkillAlias

    def user_can_leave(self, userprofile):
        """Override the parent method.

        All users can remove a skill.
        """
        return True
