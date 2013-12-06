from datetime import datetime, timedelta
import logging
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db.models import get_model

import basket
import requests
import pyes
from basket.base import request
from celery.task import task
from celery.exceptions import MaxRetriesExceededError
from elasticutils.contrib.django import get_es

from mozillians.users.managers import PUBLIC


logger = logging.getLogger(__name__)

BASKET_TASK_RETRY_DELAY = 120  # 2 minutes
BASKET_TASK_MAX_RETRIES = 2  # Total 1+2 = 3 tries
BASKET_URL = getattr(settings, 'BASKET_URL', False)
BASKET_NEWSLETTER = getattr(settings, 'BASKET_NEWSLETTER', False)
BASKET_API_KEY = os.environ.get('BASKET_API_KEY', getattr(settings, 'BASKET_API_KEY', False))
BASKET_ENABLED = all([BASKET_URL, BASKET_NEWSLETTER, BASKET_API_KEY])
INCOMPLETE_ACC_MAX_DAYS = 7


def _email_basket_managers(action, email, error_message):
    """Email Basket Managers."""
    if not getattr(settings, 'BASKET_MANAGERS', False):
        return

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

    send_mail(subject, body, settings.FROM_NOREPLY,
              settings.BASKET_MANAGERS, fail_silently=False)


@task(default_retry_delay=BASKET_TASK_RETRY_DELAY,
      max_retries=BASKET_TASK_MAX_RETRIES)
def update_basket_task(instance_id):
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
    instance = UserProfile.objects.get(pk=instance_id)

    if not BASKET_ENABLED or not instance.is_vouched:
        return

    if not instance.basket_token:
        # no token yet, they're probably not subscribed, so subscribe them.
        try:
            basket.subscribe(instance.user.email,
                             settings.BASKET_NEWSLETTER,
                             trigger_welcome='N')
        except (requests.exceptions.RequestException,
                basket.BasketException) as exception:
            try:
                update_basket_task.retry()
            except (MaxRetriesExceededError, basket.BasketException):
                _email_basket_managers('subscribe', instance.user.email,
                                       exception.message)
            return
    # Schedule the phonebook update - if we don't have a token yet,
    # phonebook update will look it up.  But delay running it for a few
    # seconds to give Basket a chance to already have the token.
    update_basket_phonebook_task.apply_async(args=[instance.user.pk], countdown=10)


@task(default_retry_delay=BASKET_TASK_RETRY_DELAY,
      max_retries=BASKET_TASK_MAX_RETRIES)
def update_basket_phonebook_task(user_pk):
    """
    Create or update profile information in the Exact Target PHONEBOOK
    data extension about the user.
    """
    instance = User.objects.get(pk=user_pk).userprofile
    email = instance.user.email
    if not BASKET_ENABLED or not instance.is_vouched:
        return

    GroupMembership = get_model('groups', 'GroupMembership')
    Group = get_model('groups', 'Group')
    data = {}
    # What groups is the user in?
    user_group_pks = (instance.groups.filter(groupmembership__status=GroupMembership.MEMBER)
                      .values_list('pk', flat=True))
    for group in Group.objects.exclude(curator=None):
        name = group.name.upper().replace(' ', '_')
        data[name] = 'Y' if group.id in user_group_pks else 'N'

    # User location if known
    if instance.country:
        data['country'] = instance.country
    if instance.city:
        data['city'] = instance.city

    # We need their token to do the update
    token = instance.basket_token
    if not token:
        msg = 'Cannot find user in Basket'
        try:
            token = instance.lookup_basket_token()
        except (requests.exceptions.RequestException,
                basket.BasketException) as exception:
            msg = exception.message
        if not token:
            # Either user not found or an exception occurred.
            # Retry either way - basket might still be in the process of setting up the user,
            # or else we got an exception and it might work next time.
            try:
                update_basket_phonebook_task.retry()
            except (MaxRetriesExceededError, basket.BasketException):
                _email_basket_managers('update_phonebook', email, msg)
            return
        # Remember the token
        # Since UserProfile.save() will trigger another update_basket_task
        # via a post-save signal, avoid calling save()
        from models import UserProfile
        UserProfile.objects.filter(user__email=email).update(basket_token=token)

    # We have a token, proceed with the update
    try:
        request('post', 'custom_update_phonebook',
                token=token, data=data)
    except (requests.exceptions.RequestException,
            basket.BasketException) as exception:
        try:
            update_basket_phonebook_task.retry()
        except (MaxRetriesExceededError, basket.BasketException):
            _email_basket_managers('update_phonebook', email,
                                   exception.message)


@task(default_retry_delay=BASKET_TASK_RETRY_DELAY,
      max_retries=BASKET_TASK_MAX_RETRIES)
def remove_from_basket_task(email, basket_token):
    """Remove from Basket Task.

    This task unsubscribes a user to Basket. The task retries on
    failure at most BASKET_TASK_MAX_RETRIES times and if it finally
    doesn't complete successfully, it emails the
    settings.BASKET_MANAGERS with details.

    """
    if not BASKET_ENABLED:
        return

    if not basket_token:
        # We don't have this user's token yet, ask basket for it
        user = User.objects.get(email=email)
        try:
            basket_token = user.userprofile.lookup_basket_token()
        except basket.BasketException as exception:
            try:
                remove_from_basket_task.retry()
            except (MaxRetriesExceededError, basket.BasketException):
                _email_basket_managers('subscribe', email, exception.message)
            return
        if not basket_token:
            logger.error('No user found with email %s' % email)
            return

        # Remember the token
        # Since UserProfile.save() will trigger another update_basket_task
        # via a post-save signal, avoid calling save()
        from models import UserProfile
        UserProfile.objects.filter(user__email=email).update(basket_token=basket_token)

    try:
        basket.unsubscribe(basket_token, email,
                           newsletters=settings.BASKET_NEWSLETTER)
    except (requests.exceptions.RequestException,
            basket.BasketException), exception:
        try:
            remove_from_basket_task.retry()
        except (MaxRetriesExceededError, basket.BasketException):
            _email_basket_managers('subscribe', email, exception.message)


@task
def index_objects(model, ids, public_index, **kwargs):
    if getattr(settings, 'ES_DISABLED', False):
        return

    es = get_es()
    qs = model.objects.filter(id__in=ids)
    if public_index:
        qs = model.objects.privacy_level(PUBLIC).filter(id__in=ids)

    for item in qs:
        model.index(model.extract_document(item.id, item),
                    bulk=True, id_=item.id, es=es, public_index=public_index)

        es.flush_bulk(forced=True)
        model.refresh_index(es=es)


@task
def unindex_objects(model, ids, public_index, **kwargs):
    if getattr(settings, 'ES_DISABLED', False):
        return

    es = get_es()
    for id_ in ids:
        try:
            model.unindex(id=id_, es=es, public_index=public_index)
        except pyes.exceptions.ElasticSearchException, e:
            # Patch pyes
            if (e.status == 404 and
                    isinstance(e.result, dict) and 'error' not in e.result):
                # Item was not found, but command did not return an error.
                # Do not worry.
                return
            else:
                raise e


@task
def remove_incomplete_accounts(days=INCOMPLETE_ACC_MAX_DAYS):
    """Remove incomplete accounts older than INCOMPLETE_ACC_MAX_DAYS old."""

    now = datetime.now() - timedelta(days=days)
    (User.objects.filter(date_joined__lt=now)
     .filter(userprofile__full_name='').delete())
