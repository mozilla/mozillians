from django.db import models
from django.dispatch import receiver
from django.template.defaultfilters import slugify

from tower import ugettext_lazy as _lazy

# If ten or more users use a group, it will get auto-completed.
AUTO_COMPLETE_COUNT = 10


class GroupBase(models.Model):
    """
    Base model for Skills and Groups

    Think of tags on a user profile.
    """
    name = models.CharField(db_index=True, max_length=50, unique=True)

    # If this is true, this Group/Skill will appear in the autocomplete list.
    auto_complete = models.BooleanField(db_index=True, default=False)
    always_auto_complete = models.BooleanField(default=False)

    class Meta:
        abstract = True

    @classmethod
    def search(cls, query, auto_complete_only=True):
        if query:
            return list(
                cls.objects.filter(
                    name__istartswith=query,
                    auto_complete=auto_complete_only
                ).values_list('name', flat=True)
            )
        return []

    def __unicode__(self):
        """Return the name of this group, unless it doesn't have one yet."""
        return getattr(self, 'name', u'Unnamed')


class Group(GroupBase):
    url = models.SlugField()
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

    class Meta:
        db_table = 'group'


class Skill(GroupBase):
    """
    Model to hold skill tags

    Like groups but without system prefs or pages/urls
    """
    pass


@receiver(models.signals.pre_save, sender=Group)
def _create_url_slug(sender, instance, raw, using, **kwargs):
    """Create a Group's URL slug when it's first saved."""
    if not instance.pk:
        instance.url = slugify(instance.name.lower())


@receiver(models.signals.pre_save, sender=Skill)
@receiver(models.signals.pre_save, sender=Group)
def _lowercase_name(sender, instance, raw, using, **kwargs):
    """Convert any group's name to lowercase before it's saved."""
    instance.name = instance.name.lower()
