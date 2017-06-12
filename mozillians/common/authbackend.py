import base64
import hashlib
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q

from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from mozillians.users.models import UserProfile, ExternalAccount


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
    """Override OIDCAuthenticationBackend to provide custom functionality."""

    def filter_users_by_claims(self, claims):
        """Override default method to add multiple emails in an account."""

        email = claims.get('email')
        request_user = self.request.user

        if not email:
            return self.UserModel.objects.none()

        account_type = ExternalAccount.TYPE_EMAIL
        alternate_emails = ExternalAccount.objects.filter(type=account_type, identifier=email)
        primary_email_qs = Q(email=email)
        alternate_email_qs = Q(userprofile__externalaccount=alternate_emails)
        user_q = self.UserModel.objects.filter(primary_email_qs | alternate_email_qs).distinct()

        # Store auth0 user_id in UserProfile
        if user_q:
            if user_q.count() == 1:
                profile_id = user_q[0].userprofile.id
                profile_qs = UserProfile.objects.filter(pk=profile_id)
                profile_qs.update(auth0_user_id=claims.get('user_id'))

        # In this case we have a registered user who is adding a secondary email
        if request_user.is_authenticated():
            if not user_q:
                ExternalAccount.objects.create(type=account_type,
                                               user=request_user.userprofile,
                                               identifier=email)
            else:
                if not user_q.filter(pk=request_user.id).exists():
                    msg = u'Email {0} already exists in the database.'.format(email)
                    messages.error(self.request, msg)
            return [request_user]
        return user_q
