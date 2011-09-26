import subprocess

from django import test
from django.contrib.auth import authenticate

import test_utils
from nose.tools import eq_

from funfactory.urlresolvers import reverse
from funfactory.manage import path

# The test data (below in module constants) must match data in
# directory/testsuite/mozillians-bulk-test-data.ldif
# You must have run x-rebuild before these tests
MOZILLIAN = dict(email='u000001@mozillians.org', uniq_id='7f3a67u000001')
PENDING = dict(email='u000003@mozillians.org', uniq_id='7f3a67u000003')
OTHER_MOZILLIAN = dict(email='u000098@mozillians.org', uniq_id='7f3a67u000098')
AMANDEEP_NAME = 'Amandeep McIlrath'
AMANDEEP_VOUCHER = '7f3a67u000001'
AMANDA_NAME = 'Amanda Younger'
PASSWORD = 'secret'


call = lambda x: subprocess.Popen(x, stdout=subprocess.PIPE).communicate()


class LDAPTestCase(test_utils.TestCase):
    @classmethod
    def setup_class(cls):
        import os
        os.environ['OPENLDAP_DB_PATH'] = '/home/vagrant/openldap-db'
        call(path('directory/devslapd/bin/x-rebuild'))

    def setUp(self):
        """
        We'll use multiple clients at the same time.
        """
        self.pending_client = mozillian_client(email=PENDING['email'],
                                               password=PASSWORD)
        self.mozillian_client = mozillian_client(email=MOZILLIAN['email'],
                                                 password=PASSWORD)


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
