import commonware.log
import cronjobs
from celery.task.sets import TaskSet
from celeryutils import chunked

from elasticutils.contrib.django import tasks
from users.models import UserProfile

log = commonware.log.getLogger('m.cron')


@cronjobs.register
def index_all_profiles():
    ids = (UserProfile.objects.values_list('id', flat=True))
    ts = [tasks.index_objects.subtask(args=[UserProfile, chunk])
          for chunk in chunked(sorted(list(ids)), 150)]
    TaskSet(ts).apply_async()
