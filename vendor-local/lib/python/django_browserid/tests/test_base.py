# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.test.client import RequestFactory

from mock import ANY, patch
from requests.exceptions import RequestException

from django_browserid.base import BrowserIDException, get_audience, verify
from django_browserid.tests import patch_settings


class GetAudienceTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch_settings(SITE_URL='http://example.com')
    def test_improperly_configured(self):
        # Raise ImproperlyConfigured if SITE_URL doesn't match the request's
        # URL.
        request = self.factory.post('/', SERVER_NAME='www.blah.com')
        with self.assertRaises(ImproperlyConfigured):
            get_audience(request)

    @patch_settings(SITE_URL='http://example.com')
    def test_properly_configured(self):
        # Return SITE_URL if it matches the request URL and DEBUG = True.
        request = self.factory.post('/', SERVER_NAME='example.com')
        self.assertEqual('http://example.com', get_audience(request))

    @patch_settings(SITE_URL=['http://example1.com', 'http://example2.com'])
    def test_iterable(self):
        # Return correct url from iterable SITE_URL, if it contains request URL.
        request = self.factory.post('/', SERVER_NAME='example2.com')
        self.assertEqual('http://example2.com', get_audience(request))

    @patch_settings(DEBUG=True)
    def test_no_site_url(self):
        # If SITE_URL isn't set, use the domain from the request.
        request = self.factory.post('/', SERVER_NAME='www.blah.com')
        self.assertEqual('http://www.blah.com', get_audience(request))


class VerifyTests(TestCase):
    def setUp(self):
        self.post_patcher = patch('django_browserid.base.requests.post')
        self.post = self.post_patcher.start()

    def tearDown(self):
        self.post_patcher.stop()

    @patch('django_browserid.base.DEFAULT_HTTP_TIMEOUT', 5)
    @patch('django_browserid.base.DEFAULT_VERIFICATION_URL',
           'https://example.com')
    @patch('django_browserid.base.DEFAULT_PROXY_INFO', None)
    @patch('django_browserid.base.DEFAULT_DISABLE_CERT_CHECK', False)
    @patch('django_browserid.base.DEFAULT_HEADERS', {'Foo': 'Bar'})
    def test_basic_success(self):
        self.post.return_value.content = """
            {"status": "okay", "email": "a@example.com"}
        """
        result = verify('asdf', 'http://testserver/')

        self.assertEqual(result, {'status': 'okay', 'email': 'a@example.com'})
        self.post.assert_called_with(
            'https://example.com',
            data={'assertion': 'asdf', 'audience': 'http://testserver/'},
            proxies=None,
            verify=True,
            headers={'Foo': 'Bar'},
            timeout=5
        )

    @patch_settings(
        BROWSERID_VERIFICATION_URL='http://example.org',
        BROWSERID_PROXY_INFO={'http': 'http://blah.example.com'},
        BROWSERID_DISABLE_CERT_CHECK=True,
        BROWSERID_HTTP_TIMEOUT=10
    )
    def test_custom_settings(self):
        verify('asdf', 'http://testserver/')
        self.post.assert_called_with(
            'http://example.org',
            data={'assertion': 'asdf', 'audience': 'http://testserver/'},
            proxies={'http': 'http://blah.example.com'},
            verify=False,
            headers=ANY,
            timeout=10
        )

    def test_custom_url(self):
        # If a custom URL is passed into verify, send the verification request
        # to that URL.
        verify('asdf', 'http://testserver/', url='https://example.com')
        self.post.assert_called_with(
            'https://example.com', data=ANY, proxies=ANY, verify=ANY,
            headers=ANY, timeout=ANY)

    def test_extra_params(self):
        # If extra params are passed into verify, they should be included with
        # the other POST arguments in the verification tests.
        verify('asdf', 'http://testserver/', extra_params={'a': 'b', 'c': 'd'})
        expected_data = {
            'assertion': 'asdf',
            'audience': 'http://testserver/',
            'a': 'b',
            'c': 'd'
        }
        self.post.assert_called_with(
            ANY, data=expected_data, proxies=ANY, verify=ANY, headers=ANY,
            timeout=ANY)

    @patch_settings(
        BROWSERID_DISABLE_CERT_CHECK=False,
        BROWSERID_CACERT_FILE='http://testserver/path/to/file'
    )
    def test_cacert_file(self):
        # If certificate verification is enabled and BROWSERID_CACERT_FILE is
        # set, the path to that file should be passed to requests in the
        # 'verify' kwarg.
        verify('asdf', 'http://testserver/')
        self.post.assert_called_with(
            ANY, data=ANY, proxies=ANY,
            verify='http://testserver/path/to/file', headers=ANY, timeout=ANY)

    def test_browserid_exception(self):
        # If requests.post raises an exception, wrap it in BrowserIDException.
        self.post.side_effect = RequestException
        with self.assertRaises(BrowserIDException):
            verify('asdf', 'http://testserver/')

    def test_invalid_json(self):
        # If the JSON returned by the verification server is invalid, return
        # False.
        self.post.return_value.content = '{invalid-json}'
        self.assertEqual(verify('asdf', 'http://testserver/'), False)

    def test_valid_json_failure(self):
        # If the verification request returns valid json with a status that
        # isn't 'okay', return False.
        self.post.return_value.content = '{"status": "failure"}'
        self.assertEqual(verify('asdf', 'http://testserver/'), False)
