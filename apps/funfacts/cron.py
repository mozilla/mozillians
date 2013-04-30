import logging

from django.core.exceptions import ValidationError
from cronjobs import register

from models import FunFact, _validate_query

logger = logging.getLogger('facts')


@register
def validate_fun_facts():
    """Validate all published facts and unpublish those failing."""
    for fact in FunFact.objects.published():
        try:
            _validate_query(fact.number)
            if fact.divisor:
                _validate_query(fact.divisor)
        except ValidationError:
            logger.error('Unpublishing fact "%s"' % fact.name)
            fact.published = False
            fact.save()
