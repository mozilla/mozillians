import commonware.log
import cronjobs
import pyes.exceptions

from celery.task.sets import TaskSet
from celeryutils import chunked
from django.conf import settings

from elasticutils.contrib.django import get_es

from tasks import index_objects
from models import PUBLIC, UserProfile

log = commonware.log.getLogger('m.cron')


@cronjobs.register
def index_all_profiles():
    # Get an es object, delete index and re-create it
    es = get_es(timeout=settings.ES_INDEXING_TIMEOUT)
    mappings = {'mappings':
                {UserProfile._meta.db_table: UserProfile.get_mapping()}}

    def _recreate_index(index):
        try:
            es.delete_index_if_exists(index)
        except pyes.exceptions.IndexMissingException:
            pass
        es.create_index(index, settings=mappings)
    _recreate_index(settings.ES_INDEXES['default'])
    _recreate_index(settings.ES_INDEXES['public'])

    # mozillians index
    ids = UserProfile.objects.complete().values_list('id', flat=True)
    ts = [index_objects.subtask(args=[UserProfile, chunk, False])
          for chunk in chunked(sorted(list(ids)), 150)]

    # public index
    ids = (UserProfile.objects.complete().public_indexable()
           .privacy_level(PUBLIC).values_list('id', flat=True))
    ts += [index_objects.subtask(args=[UserProfile, chunk, True])
           for chunk in chunked(sorted(list(ids)), 150)]

    TaskSet(ts).apply_async()
