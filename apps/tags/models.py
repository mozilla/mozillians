from django.db import models
from django.dispatch import receiver


class Tag(models.Model):
    """A Tag is an arbitrary name attached to one or more UserProfiles.

    Each Tag has a canonical name, but also a list of related names
    (usually alternative spellings, misspellings, or related terms -- e.g.
    "Add-ons" might have "addons" and "extensions" as related terms.).
    In this vein, tags should also be case-insensitive, but presented in
    their canonical case.

    Users can add their own tags to the system, but certain Tags may be
    deemed more important by admins."""
    name = models.CharField(db_index=True, max_length=50, unique=True)

    # If this is true, this Tag will appear in the autocomplete list.
    auto_complete = models.BooleanField(db_index=True, default=False)
    system = models.BooleanField(db_index=True, default=False)

    class Meta:
        db_table = 'tag'

    def _is_system(self):
        """Return True if this tag is a "system tag" (usually hidden).

        Certain tags (with a special key -- usually ":") are system tags
        that can have special meaning and are not shown by default. Instead
        of using a custom attribute and messing with a custom Manager, we
        simply denote a system tag as one with a special character.

        Users cannot create system tags.
        """
        return ':' in self.name

    def __unicode__(self):
        """Return the name of this tag, unless it doesn't have one yet."""
        return getattr(self, 'name', u'Unnamed Tag')


@receiver(models.signals.pre_save, sender=Tag)
def _denormalize_system_attribute(sender, instance, raw, using, **kwargs):
    """Mark any tags with our special system delimiter as such in the DB.

    Allows queries on system tags by searching for them via an attribute."""
    instance.system = instance._is_system()

@receiver(models.signals.pre_save, sender=Tag)
def _lowercase_name(sender, instance, raw, using, **kwargs):
    """Convert any tag's name to lowercase before it's saved."""
    instance.name = instance.name.lower()
