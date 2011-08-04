from uuid import uuid4

from nose.tools import eq_, ok_
import test_utils
from django.test.client import RequestFactory

import larper
from larper import UserSession, RegistrarSession, AdminSession

requests = []


def _mock_request(path, username='u000001@mozillians.org',
                  unique_id='7f3a67u000001', password='secret'):
    global requests
    rf = RequestFactory()
    # mock authenticated user
    request = rf.get(path)
    request.session = {}
    request.user = MockUser(username, unique_id)
    larper.store_password(request, password)
    requests.append(request)
    return request


def _with_temp_user(fn):
    """
    Runs a function in the context of a newly created user.
    It will cleanup the user after fn is run, unless it
    has already been deleted.

    fn - A callable function. First parameter should be
    a unique_id string.
    """
    regi = RegistrarSession.connect(
        _mock_request('/en-US/search?q=David'))
    username = '%s@home.net' % str(uuid4())[0:8]
    data = dict(first_name='Jane', last_name='Doe',
                username=username, password='secret password',
                biography='Keeping it real.',
                         irc_nickname='',
                         irc_nickname_unique_id='')
    new_unique_id = regi.create_person(data)

    fn(new_unique_id)

    directory = UserSession.connect(_mock_request('/en-US/search?q=David'))
    try:
        directory.get_by_unique_id(new_unique_id)

        admin = AdminSession.connect(_mock_request('/en-US/search?q=David'))
        admin.delete_person(new_unique_id)
    except:
        pass
    finally:
        pass


class MockUser(object):
    def __init__(self, username, unique_id):
        self.username = username
        self.unique_id = unique_id


class TestLarper(test_utils.TestCase):
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
                                unique_id='7f3a67u000098')

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

    def test_vouch_person(self):
        _with_temp_user(lambda u: self.vouch_person(u))

    def vouch_person(self, new_unique_id):
        request = _mock_request('/en-US/', username='u000001@mozillians.org')
        directory = self.d = UserSession.connect(request)

        ok_(directory.record_vouch('7f3a67u000001', new_unique_id))
        newbie = directory.get_by_unique_id(new_unique_id)
        eq_('7f3a67u000001', newbie.voucher_unique_id)


class TestRegistrarSession(TestLarper):
    def test_create_then_delete_person(self):
        regi = self.d = RegistrarSession.connect(
            _mock_request('/en-US/search?q=David'))
        username = '%s@home.net' % str(uuid4())[0:8]
        data = dict(first_name='Jane', last_name='Doe',
                    username=username, password='secret password',
                    biography='Keeping it real.',
                         irc_nickname='',
                         irc_nickname_unique_id='')
        new_unique_id = regi.create_person(data)

        directory = UserSession.connect(
            _mock_request('/en-US/search?q=David'))
        newbie = directory.get_by_unique_id(new_unique_id)
        eq_(username, newbie.username)

        admin = AdminSession.connect(
            _mock_request('/en-US/search?q=David'))
        admin.delete_person(new_unique_id)

        self.assertRaises(larper.NO_SUCH_PERSON, lambda:\
                              directory.get_by_unique_id(new_unique_id))
