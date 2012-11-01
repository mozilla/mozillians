import commonware.log
import cronjobs
import pyes.exceptions

from celery.task.sets import TaskSet
from celeryutils import chunked
from django.conf import settings

from elasticutils.contrib.django import get_es, tasks
from models import UserProfile

log = commonware.log.getLogger('m.cron')


@cronjobs.register
def index_all_profiles():
    # Get an es object, delete index and re-create it

    index = settings.ES_INDEXES['default']
    es = get_es()
    try:
        es.delete_index_if_exists(index)
    except pyes.exceptions.IndexMissingException:
        pass

    mappings = {'mappings':
                {UserProfile._meta.db_table: UserProfile.get_mapping()}}

    es.create_index(index, settings=mappings)

    ids = (UserProfile.objects.values_list('id', flat=True))
    ts = [tasks.index_objects.subtask(args=[UserProfile, chunk])
          for chunk in chunked(sorted(list(ids)), 150)]
    TaskSet(ts).apply_async()
