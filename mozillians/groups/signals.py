from django.db.models import signals
from django.dispatch import receiver

from mozillians.groups.models import GroupMembership


@receiver(signals.post_delete, sender=GroupMembership, dispatch_uid='delete_groupmembership_sig')
def delete_groupmembership(sender, instance, **kwargs):
    from mozillians.users.tasks import send_userprofile_to_cis

    send_userprofile_to_cis.delay(instance.userprofile.pk)
