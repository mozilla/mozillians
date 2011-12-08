from nose.tools import eq_, ok_

from django.test.client import RequestFactory

import larper
from larper import UserSession, RegistrarSession, AdminSession
from phonebook.tests import LDAPTestCase

requests = []


def _mock_request(path, username='u000001@mozillians.org',
                  unique_id='7f3a67u000001', assertion='abcdefghijklmnop'):
    global requests
    rf = RequestFactory()
    # mock authenticated user
    request = rf.get(path)
    request.session = {}
    request.user = MockUser(username, unique_id)
    larper.store_assertion(request, assertion)
    requests.append(request)
    return request


class MockUser(object):
    def __init__(self, username, unique_id):
        self.username = username
        self.unique_id = unique_id


class TestLarper(LDAPTestCase):
    def setUp(self):
        global requests
        requests = []

    def tearDown(self):
        """ Simulates middleware teardown """
        global requests
        for r in requests:
            UserSession.disconnect(r)

    def test_person_api(self):
        request = _mock_request('/en-US/search?q=David')
        directory = self.d = UserSession.connect(request)
        rs = directory.search("Bridget Hill")
        eq_(1, len(rs))
        bridget = rs[0]
        eq_('u000001@mozillians.org', bridget.username)
        eq_('7f3a67u000001', bridget.unique_id)
        eq_('Bridget', bridget.first_name)
        eq_('Hill', bridget.last_name)
        eq_('Bridget Hill', bridget.full_name)
        eq_('7f3a67u000002', bridget.voucher_unique_id)

        eq_(None, bridget.biography)

    def test_person_with_no_given_name(self):
        request = _mock_request('/en-US/')
        directory = self.d = UserSession.connect(request)
        matt = directory.get_by_unique_id("7f3a67u000002")

        eq_('u000002@mozillians.org', matt.username)
        eq_('7f3a67u000002', matt.unique_id)
        eq_('', matt.first_name)

    def test_search_is_fun(self):
        request = _mock_request('/en-US/search?q=David')
        directory = self.d = UserSession.connect(request)
        rs = directory.search("Bridget Hill")
        eq_(1, len(rs))

        rs = directory.search("u000001@mozillians.org")
        eq_(1, len(rs))

    def test_search_by_irc_nick(self):
        request = _mock_request('/en-US/')
        directory = UserSession.connect(request)
        rs = directory.search("andrew_f")
        eq_(1, len(rs))
        person = rs[0]
        eq_('Andrew Findlay', person.full_name)
        eq_('8', person.unique_id)

    def test_search_by_name(self):
        request = _mock_request('/en-US/search?q=David')
        directory = self.d = UserSession.connect(request)
        davids = directory.search_by_name("David")
        ok_(len(davids) > 0)

    def test_search_by_email(self):
        request = _mock_request('/en-US/search?q=David')
        directory = self.d = UserSession.connect(request)
        davids = directory.search_by_email("u000042@mozillians.org")
        ok_(len(davids) > 0)

    def test_get_by_unique_id(self):
        request = _mock_request('/en-US/')
        directory = self.d = UserSession.connect(request)
        directory.get_by_unique_id("7f3a67u000002")

    def test_get_by_unique_id_raises(self):
        request = _mock_request('/en-US/')
        directory = self.d = UserSession.connect(request)
        self.assertRaises(larper.NO_SUCH_PERSON, lambda:\
                              directory.get_by_unique_id("unknownid"))

    def test_update_person(self):
        unique_id = '7f3a67u000098'
        username = 'u000098@mozillians.org'
        request = _mock_request('/en-US/search?q=David',
                                username=username,
                                unique_id='7f3a67u000098',
                                assertion='somelongstring',)

        directory = self.d = UserSession.connect(request)

        amandeep = directory.get_by_unique_id(unique_id)
        first_name = amandeep.first_name
        last_name = amandeep.last_name
        eq_('Amandeep', first_name)
        eq_('McIlrath', last_name)
        eq_('Amandeep McIlrath', amandeep.full_name)

        form_data = dict(first_name='Deep',
                         last_name=last_name,
                         biography='',
                         irc_nickname='',
                         irc_nickname_unique_id='',)

        ok_(directory.update_person(unique_id, form_data))

        amandeep = directory.get_by_unique_id(unique_id)
        eq_('Deep', amandeep.first_name, 'First name edit worked')
        eq_(last_name, amandeep.last_name, 'No change')

        form_data['first_name'] = first_name
        ok_(directory.update_person(unique_id, form_data))
        amandeep = directory.get_by_unique_id(unique_id)
        eq_(first_name, amandeep.first_name)

    def vouch_person(self, new_unique_id):
        request = _mock_request('/en-US/', username='u000001@mozillians.org')
        directory = self.d = UserSession.connect(request)

        ok_(larper.record_vouch('7f3a67u000001', new_unique_id))
        newbie = directory.get_by_unique_id(new_unique_id)
        eq_('7f3a67u000001', newbie.voucher_unique_id)


class TestConnectionPooling(LDAPTestCase):
    def test_connection_pooling(self):
        # Don't use _mock_request, nor TestLarper since we want full control
        # over the request to find pooling bugs
        rf = RequestFactory()
        request = rf.get('/en-US')
        request.session = {}
        request.user = MockUser('u000001@mozillians.org', '7f3a67u000001')

        larper.store_assertion(request, 'abcdefghijklmnop')

        R = larper.READ
        W = larper.WRITE

        directory = UserSession.connect(request)
        self.assertFalse(hasattr(request, 'larper_conns'))

        regi = RegistrarSession.connect(request)
        self.assertFalse(hasattr(request, 'larper_conns'))

        regi_W_conn = regi._ensure_conn(W)
        regi_W_conn2 = regi._ensure_conn(W)

        self.assertIs(regi_W_conn, regi_W_conn2)
        self.assertTrue(hasattr(request, 'larper_conns'))
        self.assertEqual(len(request.larper_conns[R].keys()), 0)
        self.assertEqual(len(request.larper_conns[W].keys()), 1)

        dir_W_conn = directory._ensure_conn(W)
        dir_W_conn2 = directory._ensure_conn(W)

        self.assertIs(dir_W_conn, dir_W_conn2)
        self.assertEqual(len(request.larper_conns[R].keys()), 0)
        self.assertEqual(len(request.larper_conns[W].keys()), 2)

        dir_R_conn = directory._ensure_conn(R)

        admin = AdminSession.connect(request)
        admin_R_conn = admin._ensure_conn(R)
        admin_R_conn2 = admin._ensure_conn(R)
        admin_W_conn = admin._ensure_conn(W)

        self.assertIs(admin_R_conn, admin_R_conn2)
        self.assertIsNot(admin_R_conn, admin_W_conn)

        for conn in (regi_W_conn, dir_R_conn, admin_R_conn, admin_W_conn):
            # nor is it dir_R_conn2 or admin_R_conn2
            self.assertIsNot(dir_W_conn, conn)

        self.assertEqual(len(request.larper_conns[R].keys()), 2)
        self.assertEqual(len(request.larper_conns[W].keys()), 3)

        directory.disconnect(request)

        self.assertEqual(len(request.larper_conns[R].keys()), 0)
        self.assertEqual(len(request.larper_conns[W].keys()), 0)
