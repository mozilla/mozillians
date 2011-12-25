import os
import subprocess

from django import test
from django.contrib.auth import authenticate

import test_utils
from nose.tools import eq_

from funfactory.urlresolvers import reverse
from funfactory.manage import path

from users import cron

call = lambda x: subprocess.Popen(x, stdout=subprocess.PIPE).communicate()


# TODO: Remove when larper is gone.
class LDAPTestCase(test_utils.TestCase):
    @classmethod
    def setup_class(cls):
        os.environ['OPENLDAP_DB_PATH'] = '/home/vagrant/openldap-db'
        call(path('directory/devslapd/bin/x-rebuild'))

    def setUp(self):
        """We'll use multiple clients at the same time."""
        cron.vouchify()
