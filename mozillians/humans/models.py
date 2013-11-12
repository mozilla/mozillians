""" https://github.com/mozilla/kuma/blob/master/apps/humans/models.py """
import json
import subprocess

from django.conf import settings

import requests


GITHUB_REPO = 'https://api.github.com/repos/mozilla/mozillians/contributors'


class Human:
    def __init__(self):
        self.name = None
        self.website = None


class HumansTXT:
    def generate_file(self):
        githubbers = self.get_github(json.loads(requests.get(GITHUB_REPO).text))
        localizers = self.get_locales()

        target = open(settings.HUMANS_TXT, 'w')

        self.write_to_file(githubbers, target, 'Contributors on Github',
                           'Developer')
        self.write_to_file(localizers, target, 'Localization Contributors',
                           'Localizer')

        target.close()

    def write_to_file(self, humans, target, message, role):
        target.write('%s \n' % message)
        for h in humans:
            target.write('%s: %s \n' % (role, h.name.encode('ascii', 'ignore')))
            if(h.website != None):
                target.write('Website: %s \n' % h.website)
                target.write('\n')
        target.write('\n')

    def get_github(self, data=None):
        if not data:
            raw_data = json.loads(requests.get(GITHUB_REPO).text)
        else:
            raw_data = data

        humans = []
        for contributor in raw_data:
            human = Human()
            try:
                human.name = contributor['name']
            except:  # Github doesn't have a name if profile isn't filled out
                human.name = contributor['login']

            try:
                human.website = contributor['blog']
            except:
                human.website = None

            humans.append(human)

        return humans

    def get_locales(self):
        p = subprocess.Popen("svn log --quiet https://svn.mozilla.org/projects/\
                              l10n-misc/trunk/mozillians/locales/\
                              | grep '^r' | awk '{print $3}' | sort | uniq",
                              shell=True, stdout=subprocess.PIPE)
        localizers_list = p.communicate()[0].rstrip().split('\n', -1)

        humans = []
        for localizer in localizers_list:
            human = Human()
            human.name = localizer
            humans.append(human)

        return humans
