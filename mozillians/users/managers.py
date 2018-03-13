from django.apps import apps
from django.db.models import Q
from django.db.models.query import ModelIterable, QuerySet, ValuesIterable

from django.utils.translation import ugettext_lazy as _lazy


PRIVATE = 1
EMPLOYEES = 2
MOZILLIANS = 3
PUBLIC = 4
PRIVACY_CHOICES = ((MOZILLIANS, _lazy(u'Mozillians')),
                   (PUBLIC, _lazy(u'Public')))
PRIVACY_CHOICES_WITH_PRIVATE = ((MOZILLIANS, _lazy(u'Mozillians')),
                                (PUBLIC, _lazy(u'Public')),
                                (PRIVATE, _lazy(u'Private')))

PUBLIC_INDEXABLE_FIELDS = ['full_name', 'ircname', 'email']


class UserProfileValuesIterable(ValuesIterable):
    """Custom ValuesIterable to support privacy.

    Note that when you specify fields in values() you need to include
    the related privacy field in your query.

    E.g. .values('first_name', 'privacy_first_name')
    """

    def __iter__(self):
        queryset = self.queryset
        query = queryset.query
        compiler = query.get_compiler(queryset.db)
        # Purge any extra columns that haven't been explicitly asked for
        field_names = list(query.values_select)
        extra_names = list(query.extra_select)
        annotation_names = list(query.annotation_select)

        names = extra_names + field_names + annotation_names

        model_privacy_fields = query.model.privacy_fields()

        privacy_fields = [
            (names.index('privacy_%s' % field), names.index(field), field)
            for field in set(model_privacy_fields) & set(names)]

        for row in compiler.results_iter(chunked_fetch=self.chunked_fetch):
            row = list(row)
            for levelindex, fieldindex, field in privacy_fields:
                if row[levelindex] < queryset._privacy_level:
                    row[fieldindex] = model_privacy_fields[field]
            yield dict(zip(names, row))


class UserProfileModelIterable(ModelIterable):

    def __iter__(self):

        def _generator():
            self._iterator = super(UserProfileModelIterable, self).__iter__()
            while True:
                obj = self._iterator.next()
                obj._privacy_level = getattr(self.queryset, '_privacy_level')
                yield obj
        return _generator()


class UserProfileQuerySet(QuerySet):
    """Custom QuerySet to support privacy."""

    def __init__(self, *args, **kwargs):
        # TODO update public_q with external accounts
        self.public_q = Q()
        UserProfile = apps.get_model('users', 'UserProfile')
        for field in UserProfile.privacy_fields():
            key = 'privacy_%s' % field
            self.public_q |= Q(**{key: PUBLIC})

        self.public_index_q = Q()
        for field in PUBLIC_INDEXABLE_FIELDS:
            key = 'privacy_%s' % field
            if field == 'email':
                field = 'user__email'
            self.public_index_q |= (Q(**{key: PUBLIC}) & ~Q(**{field: ''}))

        super(UserProfileQuerySet, self).__init__(*args, **kwargs)
        # Override ModelIterable class to repsect the privacy_level
        self._iterable_class = UserProfileModelIterable

    def privacy_level(self, level=MOZILLIANS):
        """Set privacy level for query set."""
        self._privacy_level = level
        return self.all()

    def public(self):
        """Return profiles with at least one PUBLIC field."""
        return self.filter(self.public_q)

    def vouched(self):
        """Return complete and vouched profiles."""
        return self.complete().filter(is_vouched=True)

    def complete(self):
        """Return complete profiles."""
        return self.exclude(full_name='')

    def public_indexable(self):
        """Return public indexable profiles."""
        return self.complete().filter(self.public_index_q)

    def not_public_indexable(self):
        return self.complete().exclude(self.public_index_q)

    def _clone(self, *args, **kwargs):
        """Custom _clone with privacy level propagation."""
        c = super(UserProfileQuerySet, self)._clone(*args, **kwargs)
        c._privacy_level = getattr(self, '_privacy_level', None)
        return c

    def _values(self, *fields, **expressions):
        return super(UserProfileQuerySet, self)._values(*fields, **expressions)

    def values(self, *fields, **expressions):
        fields += tuple(expressions)
        clone = self._values(*fields, **expressions)
        clone._iterable_class = UserProfileValuesIterable
        return clone
