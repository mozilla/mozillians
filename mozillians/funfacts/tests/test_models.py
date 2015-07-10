from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase

from bleach import clean
from mock import patch
from nose.tools import assert_raises, eq_, ok_

from mozillians.funfacts.models import FunFact, _validate_query
from mozillians.funfacts.tests import FunFactFactory


class ValidateQueryTests(TestCase):
    def test_query_without_number(self):
        """Test that query without number raises ValidationError."""
        query = ''
        assert_raises(ValidationError, _validate_query, query)

    @patch('mozillians.funfacts.models.transaction', wraps=transaction)
    def test_invalid_query(self, transaction_mock):
        """Test that invalid query raises ValidationError."""
        query = 'number'
        assert_raises(ValidationError, _validate_query, query)
        transaction_mock.commit_manually.assert_called_once_with()
        transaction_mock.rollback.assert_called_once_with()

    @patch('mozillians.funfacts.models.transaction', wraps=transaction)
    def test_transaction_valid_query(self, transaction_mock):
        query = 'UserProfile.objects.aggregate(number=Count("id"))'
        _validate_query(query)
        transaction_mock.commit_manually.assert_called_once_with()
        transaction_mock.rollback.assert_called_once_with()


class FunFactManagerTests(TestCase):
    def setUp(self):
        self.published_1 = FunFactFactory.create(published=True)
        self.published_2 = FunFactFactory.create(published=True)
        self.unpublished_1 = FunFactFactory.create(published=False)

    def test_published(self):
        facts = FunFact.objects.published()
        eq_(set(facts), set([self.published_1, self.published_2]))

    def test_unpublished(self):
        facts = FunFact.objects.unpublished()
        eq_(set(facts), set([self.unpublished_1]))

    @patch('mozillians.funfacts.models.FunFact')
    def test_random(self, funfact_mock):
        FunFact.objects.random()
        funfact_mock.objects.filter.assert_called_once_with(published=True)
        (funfact_mock.objects.filter.return_value
         .order_by.assert_called_once_with('?'))


class FunFactTests(TestCase):
    @patch('mozillians.funfacts.models.ALLOWED_TAGS', ['em', 'strong'])
    @patch('mozillians.funfacts.models.bleach.clean', wraps=clean)
    def test_clean(self, clean_mock):
        text = '<strong><a href="#">foo</a></strong>'
        tags = ['em', 'strong']
        fact = FunFactFactory.create(public_text=text)
        fact.clean()
        clean_mock.assert_called_once_with(text, tags=tags, strip=True)
        eq_(fact.public_text, '<strong>foo</strong>')

    @patch('mozillians.funfacts.models.transaction', wraps=transaction)
    def test_execute_valid_funfact(self, transaction_mock):
        fact = FunFactFactory.create()
        fact.execute()
        transaction_mock.commit_manually.assert_called_once_with()
        transaction_mock.rollback.assert_called_once_with()

    @patch('mozillians.funfacts.models.transaction', wraps=transaction)
    def test_execute_invalid_funfact(self, transaction_mock):
        fact = FunFactFactory.create(number='number')
        return_value = fact.execute()
        ok_(return_value.startswith('Error'))
        transaction_mock.commit_manually.assert_called_once_with()
        transaction_mock.rollback.assert_called_once_with()
