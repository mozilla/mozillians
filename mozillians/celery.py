from __future__ import absolute_import

import os

from celery import Celery as BaseCelery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mozillians.settings')

from django.conf import settings  # noqa

RUN_DAILY = 60 * 60 * 24
RUN_HOURLY = 60 * 60
RUN_EVERY_SIX_HOURS = 6 * 60 * 60


class Celery(BaseCelery):
    def on_configure(self):
        from raven.contrib.celery import register_signal, register_logger_signal
        from raven.contrib.django.raven_compat.models import client as raven_client

        register_logger_signal(raven_client)
        register_signal(raven_client)


app = Celery('mozillians')

app.add_defaults({
    'worker_hijack_root_logger': False,
})
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


app.conf.beat_schedule = {
    'celery-healthcheck': {
        'task': 'mozillians.common.tasks.celery_healthcheck',
        'schedule': RUN_HOURLY,
        'args': ()
    },
    'invalidate-group-membership': {
        'task': 'mozillians.groups.tasks.invalidate_group_membership',
        'schedule': RUN_DAILY,
        'args': ()
    },
    'notify-membership-renewal': {
        'task': 'mozillians.groups.tasks.notify_membership_renewal',
        'schedule': RUN_DAILY,
        'args': ()
    },
    'delete-reported-spam-accounts': {
        'task': 'mozillians.users.tasks.delete_reported_spam_accounts',
        'schedule': RUN_DAILY,
        'args': ()
    },
    'periodically-send_cis_data': {
        'task': 'mozillians.users.tasks.periodically_send_cis_data',
        'schedule': RUN_EVERY_SIX_HOURS,
        'args': ()
    },
    'remove-incomplete-accounts': {
        'task': 'mozillians.users.tasks.remove_incomplete_accounts',
        'schedule': RUN_HOURLY,
        'args': ()
    }
}
