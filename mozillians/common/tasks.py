from django.conf import settings

import requests

from mozillians.celery import app


@app.task
def celery_healthcheck():
    """Ping healthchecks.io periodically to monitor celery/celerybeat health."""

    response = requests.get(settings.HEALTHCHECKS_IO_URL)
    return response.status_code == requests.codes.ok
