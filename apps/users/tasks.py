import basket
import requests
from basket.base import request
from django.core.mail import send_mail
from django.conf import settings
from celery.task import task
from celery.exceptions import MaxRetriesExceededError

from apps.groups.models import Group

BASKET_TASK_RETRY_DELAY = 120 # 2 minutes
BASKET_TASK_MAX_RETRIES = 2 # Total 1+2 = 3 tries
BASKET_URL = getattr(settings, 'BASKET_URL', False)
BASKET_NEWSLETTER = getattr(settings, 'BASKET_NEWSLETTER', False)
BASKET_ENABLED = all([BASKET_URL, BASKET_NEWSLETTER])

def _email_basket_managers(action, email, error_message):
    """Email Basket Managers."""
    if not getattr(settings, 'BASKET_MANAGERS', False):
        return

    subject = '[Mozillians - ET] '
    if action == 'subscribe':
        subject += 'Failed to subscribe or update user %s' % email
    elif action == 'unsubscribe':
        subject += 'Failed to unsubscribe user %s' % email


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
    from models import UserProfile
    instance = UserProfile.objects.get(pk=instance_id)

    if not BASKET_ENABLED or not instance.is_vouched:
        return

    data = {}
    for group in Group.objects.exclude(steward=None):
        name = group.name.upper().replace(' ', '_')
        data[name] = 'N'
        if instance.groups.filter(pk=group.id).exists():
            data[name] = 'Y'

    if instance.country:
        data['country'] = instance.country
    if instance.city:
        data['city'] = instance.city

    try:
        if not instance.basket_token:
            result = basket.subscribe(instance.user.email,
                                      settings.BASKET_NEWSLETTER,
                                      trigger_welcome='N')
            instance.basket_token = result['token']
            instance.save()

        request('post', 'custom_update_phonebook',
                token=instance.basket_token, data=data)
    except (requests.exceptions.RequestException,
            basket.BasketException), exception:
        try:
            update_basket_task.retry()
        except (MaxRetriesExceededError, basket.BasketException):
            _email_basket_managers('subscribe', instance.user.email,
                                   exception.message)


@task(default_retry_delay=BASKET_TASK_RETRY_DELAY,
      max_retries=BASKET_TASK_MAX_RETRIES)
def remove_from_basket_task(instance_id):
    """Remove from Basket Task.

    This task unsubscribes a user to Basket. The task retries on
    failure at most BASKET_TASK_MAX_RETRIES times and if it finally
    doesn't complete successfully, it emails the
    settings.BASKET_MANAGERS with details.

    """
    from models import UserProfile
    instance = UserProfile.objects.get(pk=instance_id)

    if not BASKET_ENABLED:
        return

    try:
        basket.unsubscribe(instance.basket_token, instance.user.email,
                           newsletters=settings.BASKET_NEWSLETTER)
    except (requests.exceptions.RequestException,
            basket.BasketException), exception:
        try:
            remove_from_basket_task.retry()
        except (MaxRetriesExceededError, basket.BasketException):
            _email_basket_managers('subscribe', instance.user.email,
                                   exception.message)
