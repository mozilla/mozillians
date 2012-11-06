import base64
import hashlib
import re


def validate_username(username):
    """Validate username.

    Import modules here to prevent dependency breaking.

    """
    from models import UsernameBlacklist
    username = username.lower()

    if (UsernameBlacklist.
        objects.filter(value=username, is_regex=False).exists()):
        return False

    for regex_value in UsernameBlacklist.objects.filter(is_regex=True):
        if re.match(regex_value.value, username):
            return False

    return True


def calculate_username(email):
    """Calculate username from email address.

    Import modules here to prevent dependency breaking.

    """
    from models import USERNAME_MAX_LENGTH
    from django.contrib.auth.models import User

    email = email.split('@')[0]
    username = re.sub(r'[^\w.@+-]', '-', email)
    username = username[:USERNAME_MAX_LENGTH]

    while User.objects.filter(username=username).exists():
        username += '_'

        if username > USERNAME_MAX_LENGTH:
            # We failed to calculate a name for you, default to a
            # email digest.
            username = base64.urlsafe_b64encode(
                hashlib.sha1(email).digest()).rstrip('=')

    return username
