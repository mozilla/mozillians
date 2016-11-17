import base64
import hashlib
import re

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q

from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from mozillians.users.models import ExternalAccount


def calculate_username(email):
    """Calculate username from email address."""

    email = email.split('@')[0]
    username = re.sub(r'[^\w.@+-]', '-', email)
    username = username[:settings.USERNAME_MAX_LENGTH]
    suggested_username = username
    count = 0

    while User.objects.filter(username=suggested_username).exists():
        count += 1
        suggested_username = '%s%d' % (username, count)

        if len(suggested_username) > settings.USERNAME_MAX_LENGTH:
            # We failed to calculate a name for you, default to a
            # email digest.
            return base64.urlsafe_b64encode(hashlib.sha1(email).digest()).rstrip('=')

    return suggested_username


class MozilliansAuthBackend(OIDCAuthenticationBackend):
    def filter_users_by_claims(self, claims):
        email = claims.get('email')
        if not email:
            return self.UserModel.objects.none()

        account_type = ExternalAccount.TYPE_EMAIL
        alternate_emails = ExternalAccount.objects.filter(type=account_type, identifier=email)
        primary_email_qs = Q(email=email)
        alternate_email_qs = Q(userprofile__externalaccount=alternate_emails)
        return self.UserModel.objects.filter(primary_email_qs | alternate_email_qs).distinct()
