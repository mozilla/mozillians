from django.test import TestCase

from mock import patch
from nose.tools import eq_

from mozillians.funfacts.templatetags.helpers import random_funfact
from mozillians.funfacts.tests import FunFactFactory


class HelperTests(TestCase):

    @patch('mozillians.funfacts.models.FunFact')
    def test_helper_calls_random(self, funfact_mock):
        funfact_mock.objects.random.assert_called()

    def test_helper_returns_none(self):
        """Test helper returns None when no published FunFacts."""
        FunFactFactory.create()
        eq_(random_funfact(), None)
