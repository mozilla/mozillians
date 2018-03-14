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

        register_logger_signal(raven_client, loglevel='INFO')
        register_signal(raven_client)


app = Celery('mozillians')

app.add_defaults({
    'worker_hijack_root_logger': False,
    'worker_redirect_stdouts_level': 'INFO'
})
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    from mozillians.groups.tasks import invalidate_group_membership, notify_membership_renewal
    from mozillians.users.tasks import (delete_reported_spam_accounts, periodically_send_cis_data,
                                        remove_incomplete_accounts)
    from mozillians.common.tasks import celery_healthcheck

    sender.add_periodic_task(RUN_DAILY, invalidate_group_membership.s(),
                             name='invalidate-group-membership')

    sender.add_periodic_task(RUN_DAILY, notify_membership_renewal.s(),
                             name='notify-membership-renewal')

    sender.add_periodic_task(RUN_DAILY, delete_reported_spam_accounts.s(),
                             name='delete-reported-spam-accounts')

    sender.add_periodic_task(RUN_HOURLY, celery_healthcheck.s(),
                             name='celery-healthcheck')

    sender.add_periodic_task(RUN_EVERY_SIX_HOURS, periodically_send_cis_data.s(),
                             name='periodically-send-cis-data')

    sender.add_periodic_task(RUN_HOURLY, remove_incomplete_accounts.s(),
                             name='remove-incomplete-accounts')
