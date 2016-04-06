from datetime import datetime

from django.conf import settings
from django.template.loader import render_to_string

import requests
from cronjobs import register


COMMAND = "svn log --quiet %s | grep '^r' | awk '{print $3}' | sort | uniq"


def _get_githubbers(url):
    data = requests.get(url)
    humans = []

    for contributor in data.json():
        humans.append(contributor['login'])
    return humans


@register
def generate_humanstxt():
    data = {
        'githubbers': _get_githubbers(settings.HUMANSTXT_GITHUB_REPO),
        'localizers': _get_githubbers(settings.HUMANSTXT_LOCALE_REPO),
        'last_update': datetime.utcnow(),
    }
    humans_txt = render_to_string('humans/humans.txt', data)
    with open(settings.HUMANSTXT_FILE, 'w') as output:
        output.write(humans_txt)
