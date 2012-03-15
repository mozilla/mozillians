import logging

from django.conf import settings

from jingo import register
from sorl.thumbnail import get_thumbnail


logger = logging.getLogger('common.helpers')


@register.function
def thumbnail(source, *args, **kwargs):
    """ Wraps sorl thumbnail with an additional 'default' keyword"""

    # Templates should never return an exception
    try:
        if not source:
            f = kwargs.get('default', None)
            if not f:
                f = getattr(settings, 'DEFAULT_IMAGE_SRC')
            return get_thumbnail(f, *args, **kwargs)
        return get_thumbnail(source.file, *args, **kwargs)

    except Exception as e:
        logger.error('Thumbnail had Exception: %s' % (e,))
        return None
