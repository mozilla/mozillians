from django.conf import settings

from elasticsearch import TransportError
from elasticsearch.exceptions import NotFoundError
from elasticutils.contrib.django import Indexable, MappingType, S, get_es

from mozillians.phonebook.helpers import langcode_to_name
from mozillians.users.managers import MOZILLIANS, PUBLIC

ES_MAPPING_TYPE_NAME = 'user-profile'


class PrivacyAwareS(S):

    def privacy_level(self, level=MOZILLIANS):
        """Set privacy level for query set."""
        self._privacy_level = level
        return self

    def _clone(self, *args, **kwargs):
        new = super(PrivacyAwareS, self)._clone(*args, **kwargs)
        new._privacy_level = getattr(self, '_privacy_level', None)
        return new

    def __iter__(self):
        self._iterator = super(PrivacyAwareS, self).__iter__()

        def _generator():
            while True:
                mapped_obj = self._iterator.next()
                obj = mapped_obj.get_object()
                obj._privacy_level = getattr(self, '_privacy_level', None)
                yield obj
        return _generator()


class UserProfileMappingType(MappingType, Indexable):

    @classmethod
    def get_index(cls, public_index=False):
        if public_index:
            return settings.ES_INDEXES['public']
        return settings.ES_INDEXES['default']

    @classmethod
    def get_mapping_type_name(cls):
        return ES_MAPPING_TYPE_NAME

    @classmethod
    def get_model(cls):
        from mozillians.users.models import UserProfile
        return UserProfile

    @classmethod
    def get_es(cls):
        return get_es(urls=settings.ES_URLS)

    @classmethod
    def get_mapping(cls):
        """Returns an ElasticSearch mapping."""
        return {
            'properties': {
                'id': {'type': 'integer'},
                'name': {'type': 'string', 'index': 'not_analyzed'},
                'fullname': {'type': 'string', 'analyzer': 'standard'},
                'email': {'type': 'string', 'index': 'not_analyzed'},
                'ircname': {'type': 'string', 'index': 'not_analyzed'},
                'username': {'type': 'string', 'index': 'not_analyzed'},
                'country': {'type': 'string', 'analyzer': 'whitespace'},
                'region': {'type': 'string', 'analyzer': 'whitespace'},
                'city': {'type': 'string', 'analyzer': 'whitespace'},
                'skills': {'type': 'string', 'analyzer': 'whitespace'},
                'groups': {'type': 'string', 'analyzer': 'whitespace'},
                'languages': {'type': 'string', 'index': 'not_analyzed'},
                'bio': {'type': 'string', 'analyzer': 'snowball'},
                'is_vouched': {'type': 'boolean'},
                'allows_mozilla_sites': {'type': 'boolean'},
                'allows_community_sites': {'type': 'boolean'},
                'photo': {'type': 'boolean'},
                'last_updated': {'type': 'date'},
                'date_joined': {'type': 'date'}
            }
        }

    @classmethod
    def index(cls, document, id_=None, overwrite_existing=False, es=None,
              public_index=False):
        """ Overide elasticutils.index() to support more than one index
        for UserProfile model.

        """
        if es is None:
            es = get_es()

        es.index(document, index=cls.get_index(public_index),
                 doc_type=cls.get_mapping_type(),
                 id=id_, overwrite_existing=overwrite_existing)

    @classmethod
    def refresh_index(cls, es=None, public_index=False):
        if es is None:
            es = get_es()
        index = cls.get_index(public_index)
        if es.indices.exists(index):
            es.indices.refresh(index=index)

    @classmethod
    def unindex(cls, id_, es=None, public_index=False):
        if es is None:
            es = get_es()
        try:
            es.delete(index=cls.get_index(public_index),
                      doc_type=cls.get_mapping_type_name(), id=id_)
        except NotFoundError:
            pass
        except TransportError, e:
            raise e

    @classmethod
    def extract_document(cls, obj_id, obj=None):
        """Extract the following fields from a document."""

        if obj is None:
            obj = cls.get_model().objects.get(pk=obj_id)
        doc = {}

        attrs = ('id', 'is_vouched', 'ircname',
                 'allows_mozilla_sites', 'allows_community_sites')
        for a in attrs:
            data = getattr(obj, a)
            if isinstance(data, basestring):
                data = data.lower()
            doc.update({a: data})

        doc['country'] = ([obj.geo_country.name.lower(), obj.geo_country.code]
                          if obj.geo_country else None)
        doc['region'] = obj.geo_region.name.lower() if obj.geo_region else None
        doc['city'] = obj.geo_city.name.lower() if obj.geo_city else None

        # user data
        attrs = ('username', 'email', 'last_login', 'date_joined')
        for a in attrs:
            data = getattr(obj.user, a)
            if isinstance(data, basestring):
                data = data.lower()
            doc.update({a: data})

        doc.update(dict(fullname=obj.full_name.lower()))
        doc.update(dict(name=obj.full_name.lower()))
        doc.update(dict(bio=obj.bio))
        doc.update(dict(has_photo=bool(obj.photo)))

        for attribute in ['groups', 'skills']:
            groups = []
            for g in getattr(obj, attribute).all():
                groups.extend(g.aliases.values_list('name', flat=True))
            doc[attribute] = groups
        # Add to search index language code, language name in English
        # native lanugage name.
        languages = []
        for code in obj.languages.values_list('code', flat=True):
            languages.append(code)
            languages.append(langcode_to_name(code, 'en_US').lower())
            languages.append(langcode_to_name(code, code).lower())
        doc['languages'] = list(set(languages))
        return doc

    @classmethod
    def get_indexable(cls):
        model = cls.get_model()
        return model.objects.order_by('id').values_list('id', flat=True)

    @classmethod
    def search(cls, query, include_non_vouched=False, public=False):
        """Sensible default search for UserProfiles."""
        query = query.lower().strip()
        fields = ('username', 'bio__match', 'email', 'ircname',
                  'country__match', 'country__match_phrase',
                  'region__match', 'region__match_phrase',
                  'city__match', 'city__match_phrase',
                  'fullname__match', 'fullname__match_phrase',
                  'fullname__prefix', 'fullname__fuzzy'
                  'groups__match')
        search = PrivacyAwareS(cls)
        if public:
            search = search.privacy_level(PUBLIC)
        search = search.indexes(cls.get_index(public))

        if query:
            query_dict = dict((field, query) for field in fields)
            search = (search.boost(fullname__match_phrase=5, username=5,
                                   email=5, ircname=5, fullname__match=4,
                                   country__match_phrase=4,
                                   region__match_phrase=4,
                                   city__match_phrase=4, fullname__prefix=3,
                                   fullname__fuzzy=2, bio__match=2)
                      .query(or_=query_dict))

        search = search.order_by('_score', 'name')

        if not include_non_vouched:
            search = search.filter(is_vouched=True)

        return search
