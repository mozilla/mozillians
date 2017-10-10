from __future__ import absolute_import

import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mozillians.settings')

from django.conf import settings  # noqa

RUN_DAILY = 60 * 60 * 24
RUN_HOURLY = 60 * 60

app = Celery('mozillians')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    from mozillians.groups.tasks import (invalidate_group_membership,
                                         notify_membership_renewal)
    from mozillians.users.tasks import delete_reported_spam_accounts
    from mozillians.common.tasks import celery_healthcheck

    sender.add_periodic_task(RUN_DAILY, invalidate_group_membership.s(),
                             name='invalidate-group-membership')

    sender.add_periodic_task(RUN_DAILY, notify_membership_renewal.s(),
                             name='notify-membership-renewal')

    sender.add_periodic_task(RUN_DAILY, delete_reported_spam_accounts.s(),
                             name='delete-reported-spam-accounts')

    sender.celery_healthcheck(RUN_HOURLY, celery_healthcheck.s(),
                              name='celery-healthcheck')
