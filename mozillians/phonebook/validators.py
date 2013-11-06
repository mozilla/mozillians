import re

from django.core.validators import URLValidator
from django.db.models.loading import get_model
from django.forms import ValidationError

from tower import ugettext_lazy as _lazy


def validate_username(username):
    """Validate username.

    Import modules here to prevent dependency breaking.

    """
    username = username.lower()
    UsernameBlacklist = get_model('users', 'UsernameBlacklist')

    if (UsernameBlacklist.
        objects.filter(value=username, is_regex=False).exists()):
        return False

    for regex_value in UsernameBlacklist.objects.filter(is_regex=True):
        if re.match(regex_value.value, username):
            return False

    return True


def validate_website(url):
    """Validate and return a properly formatted website url."""

    validate_url = URLValidator()

    if url and '://' not in url:
        url = u'http://%s' % url

    try:
        validate_url(url)
    except ValidationError:
        raise ValidationError(_lazy('Enter a valid URL.'))

    return url
