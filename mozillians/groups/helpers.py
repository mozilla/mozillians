from django.template.defaultfilters import slugify as django_slugify

from jingo import register
from unidecode import unidecode


@register.function
def stringify_groups(groups):
    """Change a list of Group (or skills) objects into a
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


@register.function
def user_is_curator(group, userprofile):
    """Check if a user is curator in the specific group."""
    return group.curators.filter(user=userprofile).exists()


@register.function
def is_group_instance(obj):
    """Check if the obj is of Group type."""

    # Avoid circular dependencies
    from mozillians.groups.models import Group
    return isinstance(obj, Group)
