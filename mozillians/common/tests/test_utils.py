from django.test import override_settings

from mock import patch, MagicMock
from nose.tools import eq_

from mozillians.common.tests import TestCase
from mozillians.common.utils import akismet_spam_check


class AkismetTests(TestCase):
    @patch('mozillians.common.utils.requests')
    @patch('mozillians.users.tasks.waffle.switch_is_active')
    @override_settings(AKISMET_API_KEY='akismet_api_key')
    @override_settings(SITE_URL='http://example.com')
    def test_akismet_api_spam(self, switch_is_active_mock, mock_requests):
        switch_is_active_mock.return_value = True
        response = MagicMock()
        response.text = 'true'
        mock_requests.post.return_value = response
        params = {
            'user_ip': '127.0.0.1',
            'user_agent': 'test-agent'
        }
        eq_(akismet_spam_check(**params), True)

        url = 'https://akismet_api_key.rest.akismet.com/1.1/comment-check'
        data = params
        data['blog'] = 'http://example.com'
        mock_requests.post.assert_called_with(url, data=data)

    @patch('mozillians.common.utils.requests')
    @patch('mozillians.users.tasks.waffle.switch_is_active')
    @override_settings(AKISMET_API_KEY='akismet_api_key')
    @override_settings(SITE_URL='http://example.com')
    def test_akismet_api_ham(self, switch_is_active_mock, mock_requests):
        switch_is_active_mock.return_value = True
        response = MagicMock()
        response.text = 'false'
        mock_requests.post.return_value = response
        params = {
            'user_ip': '127.0.0.1',
            'user_agent': 'test-agent'
        }
        eq_(akismet_spam_check(**params), False)

        url = 'https://akismet_api_key.rest.akismet.com/1.1/comment-check'
        data = params
        data['blog'] = 'http://example.com'
        mock_requests.post.assert_called_with(url, data=data)

    @patch('mozillians.common.utils.requests')
    @patch('mozillians.users.tasks.waffle.switch_is_active')
    @override_settings(AKISMET_API_KEY='akismet_api_key')
    @override_settings(SITE_URL='http://example.com')
    def test_akismet_api_error(self, switch_is_active_mock, mock_requests):
        switch_is_active_mock.return_value = True
        response = MagicMock()
        response.text = 'invalid'
        response.headers = {
            'x-akismet-debug-help': 'error msg'
        }
        mock_requests.post.return_value = response
        params = {
            'user_ip': '127.0.0.1',
            'user_agent': 'test-agent'
        }

        with self.assertRaises(Exception) as cm:
            akismet_spam_check(**params)

        eq_(cm.exception.message, 'Akismet raised an error: error msg')

        url = 'https://akismet_api_key.rest.akismet.com/1.1/comment-check'
        data = params
        data['blog'] = 'http://example.com'
        mock_requests.post.assert_called_with(url, data=data)
