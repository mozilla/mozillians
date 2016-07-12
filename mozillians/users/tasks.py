from datetime import datetime, timedelta
import logging
import os

from django.conf import settings
from django.core.mail import send_mail

import basket
import requests
import waffle
from celery.task import task
from celery.exceptions import MaxRetriesExceededError
from elasticutils.contrib.django import get_es
from elasticutils.utils import chunked

from mozillians.users.managers import PUBLIC


logger = logging.getLogger(__name__)

BASKET_TASK_RETRY_DELAY = 120  # 2 minutes
BASKET_TASK_MAX_RETRIES = 2  # Total 1+2 = 3 tries
BASKET_URL = getattr(settings, 'BASKET_URL', False)
BASKET_API_KEY = os.environ.get('BASKET_API_KEY', getattr(settings, 'BASKET_API_KEY', False))
BASKET_VOUCHED_NEWSLETTER = getattr(settings, 'BASKET_VOUCHED_NEWSLETTER', False)
BASKET_NDA_NEWSLETTER = getattr(settings, 'BASKET_NDA_NEWSLETTER', False)
BASKET_ENABLED = all([
    BASKET_URL,
    BASKET_API_KEY,
    BASKET_VOUCHED_NEWSLETTER,
    BASKET_NDA_NEWSLETTER
])

INCOMPLETE_ACC_MAX_DAYS = 7


def _email_basket_managers(action, email, error_message):
    """Email Basket Managers."""

    # Fallback to ADMINS emails when BASKET_MANAGERS not defined
    BASKET_MANAGERS = getattr(settings, 'BASKET_MANAGERS', None)
    recipients_list = BASKET_MANAGERS or [addr for (name, addr) in settings.ADMINS]

    subject = '[Mozillians - ET] '
    if action == 'subscribe':
        subject += 'Failed to subscribe or update user %s' % email
    elif action == 'unsubscribe':
        subject += 'Failed to unsubscribe user %s' % email
    elif action == 'update_phone_book':
        subject += 'Failed to update phone book for user %s' % email
    else:
        subject += 'Failed to %s user %s' % (action, email)

    body = """
    Something terrible happened while trying to %s user %s from Basket.

    Here is the error message:

    %s
    """ % (action, email, error_message)

    send_mail(subject, body, settings.FROM_NOREPLY, recipients_list, fail_silently=False)


@task(default_retry_delay=BASKET_TASK_RETRY_DELAY, max_retries=BASKET_TASK_MAX_RETRIES)
def update_basket_task(instance_id, newsletters=[]):
    """Update Basket Task.

    This task subscribes a user to Basket, if not already subscribed
    and then updates his data on the Phonebook DataExtension. The task
    retries on failure at most BASKET_TASK_MAX_RETRIES times and if it
    finally doesn't complete successfully, it emails the
    settings.BASKET_MANAGERS with details.

    """
    # This task is triggered by a post-save signal on UserProfile, so
    # we can't save() on UserProfile again while in here - if we were
    # running with CELERY_EAGER, we'd enter an infinite recursion until
    # Python died.

    from models import UserProfile
    try:
        instance = UserProfile.objects.get(pk=instance_id)
    except UserProfile.DoesNotExist:
        instance = None

    if (not BASKET_ENABLED or not instance or not newsletters or
            not waffle.switch_is_active('BASKET_SWITCH_ENABLED')):
        return

    email = instance.user.email
    token = instance.basket_token

    if not token:
        # no token yet, they're probably not subscribed, so subscribe them.
        # pass sync='Y' so we wait for it to complete and get back the token.
        try:
            retval = basket.subscribe(
                email,
                newsletters,
                sync='Y',
                trigger_welcome='N'
            )
        except (requests.exceptions.RequestException,
                basket.BasketException) as exception:
            try:
                update_basket_task.retry()
            except (MaxRetriesExceededError, basket.BasketException):
                _email_basket_managers('subscribe', instance.user.email,
                                       exception.message)
            return
        # Remember the token
        instance.basket_token = retval['token']
        token = retval['token']
        # Don't call .save() on a userprofile from here, it would invoke us again
        # via the post-save signal, which would be pointless.
        UserProfile.objects.filter(pk=instance.pk).update(basket_token=token)
    else:
        # They were already subscribed. See what email address they
        # have in exact target. If it has changed, we'll need to
        # unsubscribe the old address and subscribe the new one,
        # and save the new token.
        # This'll also return their subscriptions, so we can transfer them
        # to the new address if we need to.
        try:
            result = basket.lookup_user(token=token)
        except basket.BasketException as exception:
            try:
                update_basket_task.retry()
            except (MaxRetriesExceededError, basket.BasketException):
                msg = exception.message
                _email_basket_managers('update_phonebook', token, msg)
            return
        old_email = result['email']
        if old_email != email:
            try:
                # We do the new subscribe first, then the unsubscribe, so we don't
                # risk losing their subscriptions if the subscribe fails.
                # Subscribe to all the same newsletters.
                # Pass sync='Y' so we get back the new token right away
                subscribe_result = basket.subscribe(
                    email,
                    result['newsletters'],
                    sync='Y',
                    trigger_welcome='N',
                )
                # unsub all from the old token
                basket.unsubscribe(token=token, email=old_email, optout=True)
            except (requests.exceptions.RequestException,
                    basket.BasketException) as exception:
                try:
                    update_basket_task.retry()
                except (MaxRetriesExceededError, basket.BasketException):
                    _email_basket_managers('subscribe', email, exception.message)
                return
            # FIXME: We should also remove their previous phonebook record from Exact Target, but
            # basket doesn't have a custom API to do that. (basket never deletes anything.)

            # That was all successful. Update the token.
            instance.basket_token = subscribe_result['token']
            token = subscribe_result['token']
            # Don't call .save() on a userprofile from here, it would invoke us again
            # via the post-save signal, which would be pointless.
            UserProfile.objects.filter(pk=instance.pk).update(basket_token=token)


@task(default_retry_delay=BASKET_TASK_RETRY_DELAY, max_retries=BASKET_TASK_MAX_RETRIES)
def unsubscribe_from_basket_task(email, basket_token, newsletters=[]):
    """Remove from Basket Task.

    This task unsubscribes a user from the Mozillians newsletter.
    The task retries on failure at most BASKET_TASK_MAX_RETRIES times
    and if it finally doesn't complete successfully, it emails the
    settings.BASKET_MANAGERS with details.

    """
    # IMPLEMENTATION NOTE:
    #
    # This task might run AFTER the User has been deleted, so it can't
    # look anything up about the user locally. It has to make do
    # with the email and token passed in.

    if (not BASKET_ENABLED or not waffle.switch_is_active('BASKET_SWITCH_ENABLED') or
            not newsletters):
        return

    try:
        if not basket_token:
            # We don't have this user's token yet, and we need it to
            # unsubscribe.  Ask basket for it
            basket_token = basket.lookup_user(email=email)['token']

        basket.unsubscribe(basket_token, email, newsletters=newsletters)
    except (requests.exceptions.RequestException,
            basket.BasketException) as exception:
        try:
            unsubscribe_from_basket_task.retry()
        except (MaxRetriesExceededError, basket.BasketException):
            _email_basket_managers('unsubscribe', email, exception.message)


@task(default_retry_delay=BASKET_TASK_RETRY_DELAY, max_retries=BASKET_TASK_MAX_RETRIES)
def update_basket_token_task(instance_id):
    """Update basket token task

    This task looks up user email in basket and deletes the current basket_token
    if email doesn't exist in basket or updates it if it exists but it's not the same.

    """
    from models import UserProfile
    try:
        instance = UserProfile.objects.get(pk=instance_id)
    except UserProfile.DoesNotExist:
        instance = None

    if not BASKET_ENABLED or not instance or not waffle.switch_is_active('BASKET_SWITCH_ENABLED'):
        return

    try:
        token = basket.lookup_user(email=instance.email)['token']
        UserProfile.objects.filter(pk=instance.pk).update(basket_token=token)

    except basket.BasketException as exception:
        if exception.code == basket.errors.BASKET_UNKNOWN_EMAIL:
            UserProfile.objects.filter(pk=instance.pk).update(basket_token='')
            return
        update_basket_token_task.retry()
    except MaxRetriesExceededError:
        _email_basket_managers('update token', instance.email, exception.message)
    except requests.exceptions.RequestException:
        update_basket_token_task.retry()


@task
def index_objects(mapping_type, ids, chunk_size=100, public_index=False, **kwargs):
    if getattr(settings, 'ES_DISABLED', False):
        return

    es = get_es()
    model = mapping_type.get_model()

    for id_list in chunked(ids, chunk_size):
        documents = []
        qs = model.objects.filter(id__in=id_list)
        index = mapping_type.get_index(public_index)
        if public_index:
            qs = qs.public_indexable().privacy_level(PUBLIC)

        for item in qs:
            documents.append(mapping_type.extract_document(item.id, item))

        mapping_type.bulk_index(documents, id_field='id', es=es, index=index)
        mapping_type.refresh_index(es)


@task
def unindex_objects(mapping_type, ids, public_index, **kwargs):
    if getattr(settings, 'ES_DISABLED', False):
        return

    es = get_es()
    for id_ in ids:
        mapping_type.unindex(id_, es=es, public_index=public_index)


@task
def remove_incomplete_accounts(days=INCOMPLETE_ACC_MAX_DAYS):
    """Remove incomplete accounts older than INCOMPLETE_ACC_MAX_DAYS old."""
    # Avoid circular dependencies
    from mozillians.users.models import UserProfile

    now = datetime.now() - timedelta(days=days)
    (UserProfile.objects.filter(full_name='')
     .filter(user__date_joined__lt=now).delete())


@task(ignore_result=False)
def check_celery():
    """Dummy celery task to check that everything runs smoothly."""
    pass
