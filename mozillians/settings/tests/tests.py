from django.conf import settings

from nose.tools import eq_

from mozillians.common.tests import TestCase


class TestInit(TestCase):
    def test_items_per_page(self):
        """ITEMS_PER_PAGE should be multiple of 3."""
        eq_(settings.ITEMS_PER_PAGE % 3, 0)
