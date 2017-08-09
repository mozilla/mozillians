from datetime import timedelta

from django.conf import settings

import requests
from celery import periodic_task


@periodic_task(run_every=timedelta(hours=1))
def celery_healthcheck():
    """Ping healthchecks.io periodically to monitor celery/celerybeat health."""

    response = requests.get(settings.HEALTHCHECKS_IO_URL)
    return response.status_code == requests.codes.ok
