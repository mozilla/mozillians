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


def mozillian_client(email, password=PASSWORD):
    """Create and return an authorized Mozillian test client."""
    client = test.Client()

    # We can't use c.login for these tests because of some LDAP strangeness,
    # so we manually login with a POST request. (TODO: Fix this.)
    data = dict(username=email, password=password)
    user = authenticate(**data)
    user.get_profile().is_confirmed = True
    user.get_profile().save()
    # This login never works
    # TODO: deep-dive and find out why
    client.post(reverse('login'), data)
    r = client.post(reverse('login'), data, follow=True)
    eq_(email, str(r.context['user']))

    return client
