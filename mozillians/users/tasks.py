import os
from datetime import datetime, timedelta

from django.conf import settings
from django.core.mail import mail_admins, send_mail
from django.core.management import call_command
from django.db.models import Q
from django.template.loader import render_to_string

import basket
import waffle
from celery import chain, group, shared_task, Task
from celery.task import task
from celery.exceptions import MaxRetriesExceededError
from haystack import connections

from mozillians.common.utils import akismet_spam_check
from mozillians.common.templatetags.helpers import get_object_or_none


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
MOZILLIANS_URL = getattr(settings, 'SITE_URL', 'https://mozillians.org')


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
                                                source_url=MOZILLIANS_URL,
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


@task
def delete_spam_account():
    """Task to automatically delete spam accounts"""

    from mozillians.users.models import AbuseReport

    reports = AbuseReport.objects.all()

    # Manual reports deletion heuristic:
    # Delete all unvouched profiles

    query = {
        'profile__is_vouched': False,
        'is_akismet': False
    }
    reports.filter(**query).delete()

    # Automatic akismet deletion heuristic:
    # AbuseReport is created using akismet
    # AbuseReport.profile is unvouched
    # AbuseReport.profile has no skills associated

    query = {
        'is_akismet': True,
        'profile__is_vouched': False,
        'profile__skills__isnull': True,
    }
    reports.filter(**query).delete()

    # Email admins on manual reports for vouched profiles

    unvouched_not_akismet = Q(
        is_akismet=False,
        profile__is_vouched=True
    )

    akismet_has_skills = Q(
        is_akismet=True,
        profile__skills__isnull=False
    )

    reports = reports.filter(unvouched_not_akismet | akismet_has_skills).distinct()

    if reports.exists():
        subject = 'Spam profile report {}'.format(datetime.now().strftime('%x'))
        message = render_to_string('phonebook/emails/admin_spam.txt', {
            'reports': reports
        })
        mail_admins(subject, message)


@shared_task(time_limit=10 * 60)
def index_all_profiles():
    """Task to rebuild ES index without downtime."""

    ES_CONN_DEFAULT = 'default'
    ES_CONN_TMP = 'tmp'
    ES_INDEX_DEFAULT = connections[ES_CONN_DEFAULT].options['INDEX_NAME']
    ES_INDEX_TMP = connections[ES_CONN_TMP].options['INDEX_NAME']
    ES_INDEX_CURRENT = 'current_{}_{}'.format(ES_INDEX_DEFAULT, datetime.now().strftime('%s'))

    rebuild_options = {
        'using': [ES_CONN_TMP],
        'workers': settings.ES_REINDEX_WORKERS_NUM,
        'batchsize': settings.ES_REINDEX_BATCHSIZE,
        'interactive': False,
    }

    # Rebuild index in ES_INDEX_TMP
    call_command('rebuild_index', **rebuild_options)

    # Get `default` ES connection
    es_conn = connections[ES_CONN_DEFAULT].get_backend().conn

    # Create a replica of `tmp` index to be used as an alias
    tmp_index = es_conn.indices.get(ES_INDEX_TMP)
    current_index_configuration = {
        'settings': tmp_index[ES_INDEX_TMP]['settings'],
        'mappings': tmp_index[ES_INDEX_TMP]['mappings']
    }
    es_conn.indices.create(
        ES_INDEX_CURRENT,
        current_index_configuration
    )

    # Copy documents from `tmp` to alias
    reindex_query = {
        'source': {
            'index': ES_INDEX_TMP,
        },
        'dest': {
            'index': ES_INDEX_CURRENT
        }
    }

    es_conn.reindex(reindex_query)

    # Link `default` index to current
    update_aliases_query = {
        "actions": [
            {
                "add": {
                    "index": ES_INDEX_CURRENT,
                    "alias": ES_INDEX_DEFAULT
                },
            }
        ]
    }
    es_conn.indices.update_aliases(
        update_aliases_query
    )

    # Delete old aliases
    current_pattern = 'current_{}*'.format(ES_INDEX_DEFAULT)
    aliases = es_conn.indices.get(current_pattern).keys()
    old_aliases = [a for a in aliases if not a == ES_INDEX_CURRENT]
    if old_aliases:
        es_conn.indices.delete(old_aliases)

    # Cleanup `tmp` index
    options = {
        'using': [ES_CONN_TMP],
        'interactive': False
    }
    call_command('clear_index', **options)
