from django.db import models
from django.dispatch import receiver
from django.template.defaultfilters import slugify


#: If ten or more users use a group, it will get auto-completed.
AUTO_COMPLETE_COUNT = 10


class Group(models.Model):
    """A Group is an arbitrary name attached to one or more UserProfiles.

    Each Group has a canonical name, but also a list of related names
    (usually alternative spellings, misspellings, or related terms -- e.g.
    "Add-ons" might have "addons" and "extensions" as related terms.).
    In this vein, groups should also be case-insensitive, but presented in
    their canonical case.

    Users can add their own groups to the system, but certain Groups may be
    deemed more important by admins.
    """
    name = models.CharField(db_index=True, max_length=50, unique=True)
    url = models.SlugField(unique=True)

    # If this is true, this Group will appear in the autocomplete list.
    auto_complete = models.BooleanField(db_index=True, default=False)
    always_auto_complete = models.BooleanField(default=False)
    system = models.BooleanField(db_index=True, default=False)

    class Meta:
        db_table = 'group'

    def __unicode__(self):
        """Return the name of this group, unless it doesn't have one yet."""
        return getattr(self, 'name', u'Unnamed Group')


@receiver(models.signals.pre_save, sender=Group)
def _create_url_slug(sender, instance, raw, using, **kwargs):
    """Create a Group's URL slug when it's first saved."""
    if not instance.pk:
        instance.url = slugify(instance.name.lower())


@receiver(models.signals.pre_save, sender=Group)
def _lowercase_name(sender, instance, raw, using, **kwargs):
    """Convert any group's name to lowercase before it's saved."""
    instance.name = instance.name.lower()
