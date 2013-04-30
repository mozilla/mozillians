from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Count, Avg, Min, Max

import bleach

from apps.groups.models import Group, Language, Skill
from apps.mozspaces.models import MozSpace
from apps.users.models import UserProfile

ALLOWED_TAGS = ['em', 'strong']


def _validate_query(query):
    if 'number' not in query:
        raise ValidationError('Query must populate "number"')

    with transaction.commit_manually():
        try:
            eval(query)
        except BaseException, exp:
            raise ValidationError('Invalid query: %s' % exp)
        finally:
            transaction.rollback()


class FunFactManager(models.Manager):
    """ Fun Facts Manager."""

    def published(self):
        """Return published funfacts."""
        return FunFact.objects.filter(published=True)

    def unpublished(self):
        """Return unpublished funfacts."""
        return FunFact.objects.filter(unpublished=True)

    def random(self):
        """Return random picked fact or None."""
        query = FunFact.objects.filter(published=True).order_by('?')
        if query.count():
            return query[0]
        return None

class FunFact(models.Model):
    objects = FunFactManager()

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=255)
    published = models.BooleanField(default=False,
                                    choices=((True, 'Published'),
                                             (False, 'Unpublished')))
    public_text = models.TextField()
    number = models.TextField(max_length=1000, validators=[_validate_query])
    divisor = models.TextField(max_length=1000, blank=True, null=True,
                               validators=[_validate_query])

    class Meta:
        ordering = ['created']

    def __unicode__(self):
        return self.name

    def clean(self):
        self.public_text = bleach.clean(self.public_text, tags=ALLOWED_TAGS,
                                        strip=True)

    def execute(self):
        if not (self.divisor or self.number):
            return 'n/a'

        with transaction.commit_manually():
            try:
                if self.divisor:
                    number = eval(self.number)['number']
                    divisor = eval(self.divisor)['number']
                    return '%.0f%%' % (float(number)/divisor * 100)
                return '%d' % eval(self.number)['number']
            except Exception, exp:
                return 'Error: %s' % exp
            finally:
                transaction.rollback()
