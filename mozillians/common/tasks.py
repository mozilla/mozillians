from django.conf import settings

import requests

from mozillians.celery import app


@app.task
def celery_healthcheck():
    """Ping healthchecks.io periodically to monitor celery/celerybeat health."""

    url = settings.HEALTHCHECKS_IO_URL
    if not url:
        return None
    response = requests.get(url)
    return response.status_code == requests.codes.ok
