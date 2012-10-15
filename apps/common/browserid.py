import hashlib
import re

USERNAME_MAX_LENGTH = 30


def get_username(email):
    """Calculate username from email address."""
    from django.contrib.auth.models import User

    email = email.split('@')[0]
    username = re.sub(r'[^\w.@+-]', '-', email)
    username = username[:USERNAME_MAX_LENGTH]

    while User.objects.filter(username=username).exists():
        username += '_'

        if username > USERNAME_MAX_LENGTH:
            # We failed to calculate a name for you, default to a
            # email digest.
            username = hashlib.sha1(email).hexdigest()

    return username
