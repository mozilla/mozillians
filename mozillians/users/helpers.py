import base64
import hashlib
import re


USERNAME_MAX_LENGTH = 30


def calculate_username(email):
    """Calculate username from email address.

    Import modules here to prevent dependency breaking.

    """
    from django.contrib.auth.models import User

    email = email.split('@')[0]
    username = re.sub(r'[^\w.@+-]', '-', email)
    username = username[:USERNAME_MAX_LENGTH]
    suggested_username = username
    count = 0

    while User.objects.filter(username=suggested_username).exists():
        count += 1
        suggested_username = '%s%d' % (username, count)

        if len(suggested_username) > USERNAME_MAX_LENGTH:
            # We failed to calculate a name for you, default to a
            # email digest.
            return  base64.urlsafe_b64encode(
                hashlib.sha1(email).digest()).rstrip('=')

    return suggested_username
