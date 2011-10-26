import urllib

from django.contrib.auth.models import User
from django.db import models
from django.dispatch import receiver

from funfactory.utils import absolutify
from funfactory.urlresolvers import reverse

from users.models import UserProfile


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
    hidden = models.BooleanField(db_index=True, default=False)

    class Meta:
        db_table = 'tag'


    def __unicode__(self):
        """Return the name of this tag, unless it doesn't have one yet."""
        return getattr(self, 'name', u'Unnamed Tag')


# @receiver(models.signals.post_save, sender=Tag)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         UserProfile.objects.create(user=instance)

