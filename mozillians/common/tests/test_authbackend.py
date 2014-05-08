from json import loads

from mock import patch, Mock
from mozillians.common.tests import TestCase
from mozillians.common.authbackend import BrowserIDVerify
from mozillians.users.tests import UserFactory
from nose.tools import eq_, ok_


class BrowserIDVerifyTests(TestCase):
    @patch('mozillians.common.authbackend.Verify.post')
    def test_post_anonymous(self, verify_post_mock):
        Verify = BrowserIDVerify()
        request_mock = Mock()
        request_mock.user.is_authenticated.return_value = False
        Verify.request = request_mock
        Verify.post()
        verify_post_mock.assert_called_with()

    @patch('mozillians.common.authbackend.get_audience')
    @patch('mozillians.common.authbackend.RemoteVerifier.verify')
    def test_post_authenticated(self, verify_mock, get_audience_mock):
        user = UserFactory.create()
        Verify = BrowserIDVerify()
        request_mock = Mock()
        request_mock.user.is_authenticated.return_value = True
        request_mock.user = user
        request_mock.POST = {'assertion': 'assertion'}
        Verify.request = request_mock
        get_audience_mock.return_value = 'audience'
        verify_mock.return_value = Mock(email='foo@example.com')
        Verify.post()
        verify_mock.assert_called_with('assertion', 'audience')
        get_audience_mock.assert_called_with(request_mock)
        eq_(user.email, 'foo@example.com')

    @patch('mozillians.common.authbackend.BrowserIDVerify.login_failure')
    @patch('mozillians.common.authbackend.get_audience')
    @patch('mozillians.common.authbackend.RemoteVerifier.verify')
    def test_post_valid_email_exists(self, verify_mock, get_audience_mock,
                                     login_failure_mock):
        UserFactory.create(email='foo@example.com')
        user = UserFactory.create(email='la@example.com')
        Verify = BrowserIDVerify()
        request_mock = Mock()
        request_mock.user.is_authenticated.return_value = True
        request_mock.user = user
        request_mock.POST = {'assertion': 'assertion'}
        Verify.request = request_mock
        verify_mock.return_value = Mock(email='foo@example.com')
        get_audience_mock.return_value = 'audience'
        Verify.post()
        verify_mock.assert_called_with('assertion', 'audience')
        get_audience_mock.assert_called_with(request_mock)
        login_failure_mock.assert_called_with()
        ok_(Verify.change_email)

    @patch('mozillians.common.authbackend.BrowserIDVerify.login_success')
    @patch('mozillians.common.authbackend.get_audience')
    @patch('mozillians.common.authbackend.RemoteVerifier.verify')
    def test_post_change_email(self, verify_mock, get_audience_mock,
                               login_success_mock):
        user = UserFactory.create(email='la@example.com')
        Verify = BrowserIDVerify()
        request_mock = Mock()
        request_mock.user.is_authenticated.return_value = True
        request_mock.user = user
        request_mock.POST = {'assertion': 'assertion'}
        Verify.request = request_mock
        verify_mock.return_value = Mock(email='foo@example.com')
        get_audience_mock.return_value = 'audience'
        Verify.post()
        verify_mock.assert_called_with('assertion', 'audience')
        get_audience_mock.assert_called_with(request_mock)
        login_success_mock.assert_called_with()
        eq_(user.email, 'foo@example.com')
        ok_(Verify.change_email)

    def test_failure_url_email_change(self):
        Verify = BrowserIDVerify()
        Verify.change_email = True
        user = UserFactory.create(email='la@example.com')
        request_mock = Mock()
        request_mock.user.is_authenticated.return_value = True
        request_mock.user = user
        url = Verify.failure_url
        eq_(url, '/user/edit/')

    def test_login_success_email_change(self):
        Verify = BrowserIDVerify()
        Verify.change_email = True
        user = UserFactory.create(email='la@example.com')
        request_mock = Mock()
        request_mock.user.is_authenticated.return_value = True
        request_mock.user = user
        Verify.user = user
        response = loads(Verify.login_success().content)
        eq_(response['redirect'], '/u/{0}/'.format(user.username))
        eq_(response['email'], 'la@example.com')
