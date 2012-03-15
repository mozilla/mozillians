from contextlib import contextmanager

from django.conf import settings

from elasticutils import get_es

from taskboard.models import Task


@contextmanager
def create_and_index_task(**kwargs):
    """
    Create a new video object, with default acceptable values. The video
    is deleted once the block is exited.
    """
    args = {
        'contact': None,
        'summary': 'Test summary',
        'instructions': 'test instructions',
    }
    args.update(kwargs)

    task = Task.objects.create(**args)

    # Refresh ES if possible.
    if not settings.ES_DISABLED:
        get_es().refresh(settings.ES_INDEXES['default'], timesleep=0)

    yield task
    task.delete()
