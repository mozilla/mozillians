import subprocess
from datetime import datetime

from django.conf import settings
from django.template.loader import render_to_string

import requests
from cronjobs import register


COMMAND = "svn log --quiet %s | grep '^r' | awk '{print $3}' | sort | uniq"


def _get_githubbers():
    data = requests.get(settings.HUMANSTXT_GITHUB_REPO)
    humans = []

    for contributor in data.json():
        humans.append(contributor['login'])
    return humans


def _get_localizers():
    command = COMMAND % (settings.HUMANSTXT_LOCALE_REPO)
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    data = process.communicate()[0].rstrip().split('\n', -1)
    humans = []

    for contributor in data:
        humans.append(contributor)
    return humans


@register
def generate_humanstxt():
    data = {
        'githubbers': _get_githubbers(),
        'localizers': _get_localizers(),
        'last_update': datetime.utcnow(),
    }
    humans_txt = render_to_string('humans/humans.txt', data)
    with open(settings.HUMANSTXT_FILE, 'w') as output:
        output.write(humans_txt)
