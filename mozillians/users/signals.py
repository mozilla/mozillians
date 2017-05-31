from django.db.models import signals
from django.dispatch import receiver
from django.conf import settings
from django.contrib.auth.models import User

from multidb.pinning import use_master

from mozillians.users.models import ExternalAccount, UserProfile, Vouch
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
    if instance.user:
        instance.user.delete()


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

    with use_master:
        vouches_qs = Vouch.objects.filter(vouchee=profile)
        vouches = vouches_qs.count()

    profile.is_vouched = vouches > 0
    profile.can_vouch = vouches >= settings.CAN_VOUCH_THRESHOLD
    profile.save(**{'autovouch': False})


@receiver(signals.post_save, sender=ExternalAccount, dispatch_uid='add_employee_vouch_sig')
def add_employee_vouch(sender, instance, **kwargs):
    """Add a vouch if an alternate email address is a mozilla* address."""

    if kwargs.get('raw') or not instance.type == ExternalAccount.TYPE_EMAIL:
        return
    instance.user.auto_vouch()
