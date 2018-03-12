from django.test import TestCase

from mock import patch
from nose.tools import eq_

from mozillians.funfacts.templatetags.helpers import random_funfact
from mozillians.funfacts.tests import FunFactFactory


class HelperTests(TestCase):

    @patch('mozillians.funfacts.templatetags.helpers.FunFact')
    def test_helper_calls_random(self, funfact_mock):
        """Test helper calls `random` when published FunFacts exist"""

        # Assume that we have 42 published funfacts
        funfact_mock.objects.published.count.return_value = 42
        random_funfact()
        funfact_mock.objects.random.assert_called()

    def test_helper_returns_none(self):
        """Test helper returns None when no published FunFacts."""
        FunFactFactory.create()
        eq_(random_funfact(), None)
