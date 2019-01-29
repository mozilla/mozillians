import json
import logging
from django.db import transaction
from django.db.models import signals
from django.dispatch import receiver
from django.conf import settings
from django.contrib.auth.models import User

from raven.contrib.django.raven_compat.models import client as sentry_client

from mozillians.common.utils import bundle_profile_data
from mozillians.groups.models import Group
from mozillians.users.models import UserProfile, Vouch
from mozillians.users.tasks import subscribe_user_to_basket, unsubscribe_from_basket_task


# Signal to create a UserProfile.
@receiver(signals.post_save, sender=User, dispatch_uid='create_user_profile_sig')
def create_user_profile(sender, instance, created, raw, **kwargs):
    if not raw:
        up, created = UserProfile.objects.get_or_create(user=instance)
        if not created:
            signals.post_save.send(sender=UserProfile, instance=up, created=created, raw=raw)


# Signal to remove the User object when a profile is deleted
@receiver(signals.post_delete, sender=UserProfile, dispatch_uid='delete_user_obj_sig')
def delete_user_obj_sig(sender, instance, **kwargs):
    with transaction.atomic():
        if instance.user:
            instance.user.delete()


# Signal to remove the UserProfile from all the access groups and update the curator
@receiver(signals.pre_delete, sender=UserProfile,
          dispatch_uid='remove_user_from_access_groups_sig')
def remove_user_from_access_groups(sender, instance, **kwargs):
    """Updates the curators of access groups in case the profile to be deleted

    is a curator.
    """
    groups = Group.objects.filter(is_access_group=True, curators=instance)
    for group in groups:
        # If the user is the only curator of an access group
        # add all the super users as curators and remove the user
        if not group.curator_can_leave(instance):
            for super_user in UserProfile.objects.filter(user__is_superuser=True):
                group.curators.add(super_user)
                if not group.has_member(super_user):
                    group.add_member(super_user)
        group.curators.remove(instance)


# Basket User signals
@receiver(signals.post_save, sender=UserProfile, dispatch_uid='update_basket_sig')
def update_basket(sender, instance, **kwargs):
    newsletters = [settings.BASKET_VOUCHED_NEWSLETTER]
    if instance.is_vouched:
        subscribe_user_to_basket.delay(instance.id, newsletters)
    else:
        unsubscribe_from_basket_task.delay(instance.email, newsletters)


@receiver(signals.pre_delete, sender=UserProfile, dispatch_uid='unsubscribe_from_basket_sig')
def unsubscribe_from_basket(sender, instance, **kwargs):
    newsletters = [settings.BASKET_VOUCHED_NEWSLETTER, settings.BASKET_NDA_NEWSLETTER]
    unsubscribe_from_basket_task.delay(instance.email, newsletters)


# Signals related to CIS operations
@receiver(signals.pre_delete, sender=UserProfile, dispatch_uid='push_empty_groups_to_cis_sig')
def push_empty_groups_to_cis(sender, instance, **kwargs):
    """Notify CIS about the profile deletion.

    Remove all the access groups and tags from the profile.
    """
    from mozillians.users.tasks import send_userprofile_to_cis
    data = bundle_profile_data(instance.id, delete=True)

    for d in data:
        log_name = 'CIS group deletion - {}'.format(d['user_id'])
        log_data = {
            'level': logging.DEBUG,
            'logger': 'mozillians.cis_transaction'
        }
        log_extra = {
            'cis_transaction_data': json.dumps(d)
        }

        sentry_client.captureMessage(log_name, data=log_data, stack=True, extra=log_extra)

    send_userprofile_to_cis.delay(profile_results=data)


# Signals related to vouching.
@receiver(signals.post_delete, sender=Vouch, dispatch_uid='update_vouch_flags_delete_sig')
@receiver(signals.post_save, sender=Vouch, dispatch_uid='update_vouch_flags_save_sig')
def update_vouch_flags(sender, instance, **kwargs):
    if kwargs.get('raw'):
        return
    try:
        profile = instance.vouchee
    except UserProfile.DoesNotExist:
        # In this case we delete not only the vouches but the
        # UserProfile as well. Do nothing.
        return

    vouches_qs = Vouch.objects.filter(vouchee=profile)
    vouches = vouches_qs.count()

    profile.is_vouched = vouches > 0
    profile.can_vouch = vouches >= settings.CAN_VOUCH_THRESHOLD
    profile.save(**{'autovouch': False})
