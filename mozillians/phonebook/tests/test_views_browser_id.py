from mock import patch, Mock
from mozillians.common.tests import TestCase
from mozillians.phonebook.views import BrowserIDVerify
from mozillians.users.tests import UserFactory
from nose.tools import eq_


class BrowserIDVerifyTests(TestCase):
    @patch('mozillians.phonebook.views.Verify.form_valid')
    def test_form_valid_anonymous(self, form_valid_mock):
        Verify = BrowserIDVerify()
        request_mock = Mock()
        request_mock.user.is_authenticated.return_value = False
        Verify.request = request_mock
        form = Mock()
        Verify.form_valid(form)
        form_valid_mock.assert_called_with(form)

    @patch('mozillians.phonebook.views.get_audience')
    @patch('mozillians.phonebook.views.verify')
    def test_form_valid_authenticated(self, verify_mock, get_audience_mock):
        user = UserFactory.create()
        Verify = BrowserIDVerify()
        request_mock = Mock()
        request_mock.user.is_authenticated.return_value = True
        request_mock.user = user
        Verify.request = request_mock
        form = Mock()
        form.cleaned_data = {'assertion': 'assertion'}
        get_audience_mock.return_value = 'audience'
        verify_mock.return_value = {'email': 'foo@bar.com'}

        Verify.form_valid(form)

        verify_mock.assert_called_with('assertion', 'audience')
        get_audience_mock.assert_called_with(request_mock)
        eq_(user.email, 'foo@bar.com')

    @patch('mozillians.phonebook.views.get_audience')
    @patch('mozillians.phonebook.views.verify')
    def test_form_valid_email_exists(self, verify_mock, get_audience_mock):
        UserFactory.create(email='foo@bar.com')
        user = UserFactory.create(email='la@example.com')
        Verify = BrowserIDVerify()
        request_mock = Mock()
        request_mock.user.is_authenticated.return_value = True
        request_mock.user = user
        Verify.request = request_mock
        form = Mock()
        form.cleaned_data = {'assertion': 'assertion'}
        get_audience_mock.return_value = 'audience'
        verify_mock.return_value = {'email': 'foo@bar.com'}

        Verify.form_valid(form)

        verify_mock.assert_called_with('assertion', 'audience')
        get_audience_mock.assert_called_with(request_mock)
        eq_(user.email, 'la@example.com')
