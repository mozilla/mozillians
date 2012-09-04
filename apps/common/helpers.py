import logging

from django.conf import settings

from jingo import register
from sorl.thumbnail import get_thumbnail


logger = logging.getLogger('common.helpers')


@register.function
def thumbnail(source, *args, **kwargs):
    """Wraps sorl thumbnail with an additional 'default' keyword."""

    # Templates should never return an exception
    try:
        if not source.path:
            source = kwargs.get('default')
        return get_thumbnail(source, *args, **kwargs)
    except Exception as e:
        logger.error('Thumbnail had Exception: %s' % e)
        source = getattr(settings, 'DEFAULT_IMAGE_SRC')
        return get_thumbnail(source, *args, **kwargs)
