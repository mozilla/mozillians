from django.conf import settings

import cronjobs

from celery.task.sets import TaskSet
from celeryutils import chunked
from elasticutils.contrib.django import get_es

from mozillians.users.tasks import index_objects
from mozillians.users.models import UserProfile, UserProfileMappingType


@cronjobs.register
def index_all_profiles():
    # Get an es object, delete index and re-create it
    es = get_es(timeout=settings.ES_INDEXING_TIMEOUT)
    mappings = {'mappings':
                {UserProfileMappingType.get_mapping_type_name():
                 UserProfileMappingType.get_mapping()}}

    def _recreate_index(index):
        es.indices.delete(index=index, ignore=[400, 404])
        es.indices.create(index, body=mappings)

    _recreate_index(settings.ES_INDEXES['default'])
    _recreate_index(settings.ES_INDEXES['public'])

    # mozillians index
    ids = UserProfile.objects.complete().values_list('id', flat=True)
    ts = [index_objects.subtask(args=[UserProfileMappingType, chunk, 150, False])
          for chunk in chunked(sorted(list(ids)), 150)]

    # public index
    ts += [index_objects.subtask(args=[UserProfileMappingType, chunk, 150, True])
           for chunk in chunked(sorted(list(ids)), 150)]

    TaskSet(ts).apply_async()
