import subprocess

from django import test

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
AMANDEEP_VOUCHER = 'cn=test,ou=People,dc=mozillians,dc=org'
AMANDA_NAME = 'Amanda Younger'
PASSWORD = 'secret'


def pending_user_client():
    client = test.Client()
    # We can't use client.login for these tests
    url = reverse('login')
    data = dict(username=PENDING['email'], password=PASSWORD)
    client.post(url, data, follow=True)
    # HACK Something is seriously hozed here...
    # First visit to /login always fails, so we make
    # second request... WTF
    client = test.Client()
    url = reverse('login')
    r = client.post(url, data, follow=True)
    eq_(r.status_code, 200, "Something broke. Got a %d error." % r.status_code)
    eq_(PENDING['email'], str(r.context['user']))
    return client


def mozillian_client():
    client = test.Client()
    # We can't use c.login for these tests
    url = reverse('login')
    data = dict(username=MOZILLIAN['email'], password=PASSWORD)
    r = client.post(url, data, follow=True)
    eq_(MOZILLIAN['email'], str(r.context['user']))
    return client

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
        self.pending_client = pending_user_client()
        self.mozillian_client = mozillian_client()
