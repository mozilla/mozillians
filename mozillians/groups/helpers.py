from django.template.defaultfilters import slugify as django_slugify

from jingo import register
from unidecode import unidecode


@register.function
def stringify_groups(groups):
    """Change a list of Group (or skills or languages) objects into a
    space-delimited string.

    """
    return u','.join([group.name for group in groups])


def slugify(s):
    """Slugify function that dumbs down but preserves non-Latin chars"""

    # unidecode complains if input is not unicode, but for our case, it
    # doesn't really matter
    if isinstance(s, str):
        s = unicode(s)
    return django_slugify(unidecode(s))
