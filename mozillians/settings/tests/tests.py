from django.conf import settings
from django.test.client import Client

from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase


class TestSettings(TestCase):
    def test_items_per_page(self):
        """ITEMS_PER_PAGE should be multiple of 3."""
        eq_(settings.ITEMS_PER_PAGE % 3, 0)

    def test_csp_in_installed_apps(self):
        ok_('csp' in settings.INSTALLED_APPS)

    def test_csp_headers_set(self):
        client = Client()
        response = client.get('/', follow=True)
        ok_(response.has_header('Content-Security-Policy'))
