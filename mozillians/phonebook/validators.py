import re

from django.core.validators import URLValidator, email_re
from django.db.models.loading import get_model
from django.forms import ValidationError

from tower import ugettext as _


def validate_twitter(username):
    """Return a twitter username given '@' or http(s) strings."""

    if username:
        username = re.sub('https?://(www\.)?twitter\.com/|@', '', username)

        # Twitter accounts must be alphanumeric ASCII including underscore, and <= 15 chars.
        # https://support.twitter.com/articles/101299-why-can-t-i-register-certain-usernames
        if len(username) > 15:
            raise ValidationError(_('Twitter usernames cannot be longer than 15 characters.'))

        if not re.match('^\w+$', username):
            raise ValidationError(_('Twitter usernames must contain only alphanumeric'
                                    ' characters and the underscore.'))
    return username


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
        raise ValidationError(_('Enter a valid URL.'))

    return url


def validate_username_not_url(username):
    """Validate that a username is not a URL."""

    if username.startswith('http://') or username.startswith('https://'):
        raise ValidationError(_('This field requires an identifier, not a URL.'))

    return username


def validate_email(value):
    """Validate that a username is email like."""
    if not email_re.match(value):
        raise ValidationError(_('Enter a valid address.'))
    return value


def validate_phone_number(value):
    """Validate that a phone number is in international format. (5-15 characters)."""
    value = value.replace(' ', '')
    value = re.sub(r'^00', '+', value)

    # Ensure that there are 5 to 15 digits
    pattern = re.compile(r'^\+\d{5,15}$')
    if not pattern.match(value):
        raise ValidationError(_('Please enter a valid phone number in international format '
                                '(e.g. +1 555 555 5555)'))

    return value
