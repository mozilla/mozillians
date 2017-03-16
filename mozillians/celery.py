from __future__ import absolute_import

import os

from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mozillians.settings')

from django.conf import settings  # noqa

RUN_DAILY = 60 * 60 * 24

app = Celery('mozillians')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    from mozillians.groups.tasks import notify_membership_renewal, invalidate_group_membership

    sender.add_periodic_task(RUN_DAILY, invalidate_group_membership.s(),
                             name='invalidate-group-membership')

    sender.add_periodic_task(RUN_DAILY, notify_membership_renewal.s(),
                             name='notify-membership-renewal')
