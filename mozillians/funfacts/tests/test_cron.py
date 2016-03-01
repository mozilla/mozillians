from django.test import TestCase

from mock import call, patch
from nose.tools import eq_

from mozillians.funfacts.cron import validate_fun_facts
from mozillians.funfacts.models import FunFact, _validate_query
from mozillians.funfacts.tests import FunFactFactory


class CronTests(TestCase):
    @patch('mozillians.funfacts.cron._validate_query', wraps=_validate_query)
    def test_cron_validator(self, validator_mock):
        valid_fact_1 = FunFactFactory.create(published=True)
        valid_fact_2 = FunFactFactory.create(
            published=True,
            divisor='UserProfile.objects.aggregate(number=Count("id"))')
        invalid_fact_1 = FunFactFactory.create(published=True, number='invalid')
        invalid_fact_2 = FunFactFactory.create(published=True, divisor='invalid')
        validate_fun_facts()
        call_list = [call(valid_fact_1.number),
                     call(valid_fact_2.number),
                     call(valid_fact_2.divisor),
                     call(invalid_fact_1.number),
                     call(invalid_fact_2.number),
                     call(invalid_fact_2.divisor)]
        eq_(validator_mock.call_args_list, call_list)
        invalid_fact_1 = FunFact.objects.get(id=invalid_fact_1.id)
        invalid_fact_2 = FunFact.objects.get(id=invalid_fact_2.id)
        eq_(invalid_fact_1.published, False)
        eq_(invalid_fact_2.published, False)
