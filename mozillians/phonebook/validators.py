import re

from mozillians.users.models import UsernameBlacklist


def validate_username(username):
    """Validate username.

    Import modules here to prevent dependency breaking.

    """
    username = username.lower()

    if (UsernameBlacklist.
        objects.filter(value=username, is_regex=False).exists()):
        return False

    for regex_value in UsernameBlacklist.objects.filter(is_regex=True):
        if re.match(regex_value.value, username):
            return False

    return True
