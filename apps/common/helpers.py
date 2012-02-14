from jingo import register
from sorl.thumbnail import get_thumbnail


@register.function
def thumbnail(source, *args, **kwargs):
    """
    Wraps sorl thumbnail with an additional 'default" keyword if the source
    image is not found.
    """
    if not source:
        source = kwargs.get('default', None)
    try:
        # Templates should never return an exception
        return get_thumbnail(source, *args, **kwargs)
    except Exception:
        return None

