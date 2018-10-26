from django.db.models import signals

from haystack.signals import BaseSignalProcessor

from mozillians.users.models import IdpProfile, UserProfile
from mozillians.groups.models import Group


# Django Haystack signals
class SearchSignalProcessor(BaseSignalProcessor):

    def setup(self):
        signals.post_save.connect(self.handle_save, sender=UserProfile)
        signals.post_delete.connect(self.handle_delete, sender=UserProfile)
        signals.post_save.connect(self.handle_save, sender=Group)
        signals.post_delete.connect(self.handle_delete, sender=Group)
        signals.post_save.connect(self.handle_save, sender=IdpProfile)
        signals.post_delete.connect(self.handle_delete, sender=IdpProfile)

    def handle_save(self, sender, instance, **kwargs):
        # Do not index incomplete profiles and not visible groups.
        if ((isinstance(instance, UserProfile) and instance.is_complete)
            or (isinstance(instance, Group) and instance.visible)
                or (isinstance(instance, IdpProfile))):
            super(SearchSignalProcessor, self).handle_save(sender, instance, **kwargs)

    def teardown(self):
        signals.post_save.disconnect(self.handle_save, sender=UserProfile)
        signals.post_delete.disconnect(self.handle_delete, sender=UserProfile)
        signals.post_save.disconnect(self.handle_save, sender=Group)
        signals.post_delete.disconnect(self.handle_delete, sender=Group)
        signals.post_save.disconnect(self.handle_save, sender=IdpProfile)
        signals.post_delete.disconnect(self.handle_delete, sender=IdpProfile)
