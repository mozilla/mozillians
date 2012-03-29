from django.db import models
from django.dispatch import receiver
from django.template.defaultfilters import slugify


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
