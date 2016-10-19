import os
from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import send_mail

import basket
import waffle
from celery import chain, group, shared_task, Task
from celery.task import task
from celery.exceptions import MaxRetriesExceededError
from elasticutils.contrib.django import get_es
from elasticutils.utils import chunked

from mozillians.common.utils import akismet_spam_check
from mozillians.common.templatetags.helpers import get_object_or_none
from mozillians.users.managers import PUBLIC


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
MOZILLIANS_NEWSLETTERS = [BASKET_NDA_NEWSLETTER, BASKET_VOUCHED_NEWSLETTER]


class DebugBasketTask(Task):
    """Base Error Handing Abstract class for all the Basket Tasks."""
    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        # Fallback to ADMINS emails when BASKET_MANAGERS not defined
        basket_managers = getattr(settings, 'BASKET_MANAGERS', None)
        recipients_list = basket_managers or [addr for (_, addr) in settings.ADMINS]

        subject = '[Mozillians - ET] Traceback {0}'.format(task_id)

        body = """
        Something terrible happened for task {task_id}

        Here is the error message:

        exception: {exc}

        args: {args}

        kwargs: {kwargs}

        exception info: {einfo}

        """.format(task_id=task_id, exc=exc, args=args, kwargs=kwargs, einfo=einfo)

        send_mail(subject, body, settings.FROM_NOREPLY, recipients_list, fail_silently=False)


@shared_task(bind=True, base=DebugBasketTask, default_retry_delay=BASKET_TASK_RETRY_DELAY,
             max_retries=BASKET_TASK_MAX_RETRIES)
def lookup_user_task(self, email):
    """Task responsible for getting information about a user in basket."""

    # We need to return always a dictionary for the next task
    result = {}

    try:
        result = basket.lookup_user(email=email)
    except MaxRetriesExceededError as exc:
        raise exc
    except basket.BasketException as exc:
        if not exc[0] == u'User not found':
            raise self.retry(exc=exc)
        result = exc.result
    return result


@shared_task(bind=True, base=DebugBasketTask, default_retry_delay=BASKET_TASK_RETRY_DELAY,
             max_retries=BASKET_TASK_MAX_RETRIES)
def subscribe_user_task(self, result, email='', newsletters=[], sync='N', trigger_welcome='N'):
    """Subscribes a user to basket newsletters.

    The email to subscribe is provided either from the result of the lookup task
    or from the profile of the user.
    """

    if not result and not email:
        return None

    newsletters_to_subscribe = []
    if result.get('status') == 'ok':
        # This is used when we want to subscribe a different email
        # than the one in the lookup (eg when a user changes emails)
        if not email:
            email = result.get('email')

        if newsletters:
            newsletters_to_subscribe = list(set(newsletters) - set(result['newsletters']))
        else:
            # This case is used when a user changes email.
            # The lookup task will provide the newsletters that the user was registered.
            # We need to find the common with the mozillians newsletters and
            # subscribe the email provided as an argument.
            newsletters_to_subscribe = list(set(MOZILLIANS_NEWSLETTERS)
                                            .intersection(result['newsletters']))

    # The lookup failed because the user does not exist. We have a new user!
    if (result.get('status') == 'error' and
            result.get('desc') == u'User not found' and newsletters):
        newsletters_to_subscribe = newsletters

    if newsletters_to_subscribe:
        try:
            subscribe_result = basket.subscribe(email,
                                                newsletters_to_subscribe,
                                                sync=sync,
                                                trigger_welcome=trigger_welcome,
                                                api_key=BASKET_API_KEY)
        except MaxRetriesExceededError as exc:
            raise exc
        except basket.BasketException as exc:
            raise self.retry(exc=exc)
        return subscribe_result
    return None


@shared_task(bind=True, base=DebugBasketTask, default_retry_delay=BASKET_TASK_RETRY_DELAY,
             max_retries=BASKET_TASK_MAX_RETRIES)
def unsubscribe_user_task(self, result, newsletters=[], optout=False):
    """Removes a user from the Basket subscription."""

    if not result:
        return None

    newsletters_to_unsubscribe = []
    if result.get('status') == 'ok':
        email = result.get('email')
        token = result.get('token')

        # only unsubscribe from our newsletters
        if newsletters:
            newsletters_to_unsubscribe = list(set(newsletters).intersection(result['newsletters']))
        else:
            newsletters_to_unsubscribe = list(set(MOZILLIANS_NEWSLETTERS)
                                              .intersection(result['newsletters']))

    # Unsubscribe the calculated newsletters
    if newsletters_to_unsubscribe:
        try:
            unsubscribe_result = basket.unsubscribe(token=token,
                                                    email=email,
                                                    newsletters=newsletters_to_unsubscribe,
                                                    optout=optout)
        except MaxRetriesExceededError as exc:
            raise exc
        except basket.BasketException as exc:
            raise self.retry(exc=exc)
        return unsubscribe_result
    return None


@shared_task()
def subscribe_user_to_basket(instance_id, newsletters=[]):
    """Subscribe a user to Basket.

    This task subscribes a user to Basket, if not already subscribed
    and then updates his data on the Phonebook DataExtension. The task
    retries on failure at most BASKET_TASK_MAX_RETRIES times and if it
    finally doesn't complete successfully, it emails the
    settings.BASKET_MANAGERS with details.
    """

    from mozillians.users.models import UserProfile
    try:
        instance = UserProfile.objects.get(pk=instance_id)
    except UserProfile.DoesNotExist:
        instance = None

    if (not BASKET_ENABLED or not instance or not newsletters or
            not waffle.switch_is_active('BASKET_SWITCH_ENABLED')):
        return

    lookup_subtask = lookup_user_task.subtask((instance.user.email,))
    subscribe_subtask = subscribe_user_task.subtask((instance.user.email, newsletters,))
    chain(lookup_subtask | subscribe_subtask)()


@shared_task()
def update_email_in_basket(old_email, new_email):
    """Update user emails in Basket.

    This task is triggered when users change their email.
    The task checks whether the user is already subscribed with the old email.
    If there is a subscription we remove it and we register the new email.
    """
    if not BASKET_ENABLED or not waffle.switch_is_active('BASKET_SWITCH_ENABLED'):
        return

    chain(
        lookup_user_task.subtask((old_email,)) |
        group(
            subscribe_user_task.subtask((new_email,)),
            unsubscribe_user_task.subtask()
        )
    ).delay()


@shared_task()
def unsubscribe_from_basket_task(email, newsletters=[]):
    """Remove user from Basket Task.

    This task unsubscribes a user from the Mozillians newsletter.
    """
    if not BASKET_ENABLED or not waffle.switch_is_active('BASKET_SWITCH_ENABLED'):
        return

    # Lookup the email and then pass the result to the unsubscribe subtask
    chain(
        lookup_user_task.subtask((email,)) |
        unsubscribe_user_task.subtask((newsletters,))
    ).delay()


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
    UserProfile.objects.filter(full_name='').filter(user__date_joined__lt=now).delete()


@task(ignore_result=False)
def check_celery():
    """Dummy celery task to check that everything runs smoothly."""
    pass


@task
def check_spam_account(instance_id, **kwargs):
    """Task to check if profile is spam according to akismet"""
    # Avoid circular dependencies
    from mozillians.users.models import AbuseReport, UserProfile

    spam = akismet_spam_check(**kwargs)
    profile = get_object_or_none(UserProfile, id=instance_id)

    if spam and profile:
        kwargs = {
            'type': AbuseReport.TYPE_SPAM,
            'profile': profile,
            'reporter': None,
            'is_akismet': True,
        }

        AbuseReport.objects.get_or_create(**kwargs)
