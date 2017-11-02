import base64
import hashlib
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from mozillians.common.templatetags.helpers import get_object_or_none
from mozillians.users.models import IdpProfile
from mozillians.users.tasks import send_userprofile_to_cis


# Only allow the following login flows
# Passwordless > Google > Github > LDAP
# There is no way to downgrade
ALLOWED_IDP_FLOWS = {
    IdpProfile.PROVIDER_PASSWORDLESS: [
        IdpProfile.PROVIDER_PASSWORDLESS,
        IdpProfile.PROVIDER_GOOGLE,
        IdpProfile.PROVIDER_GITHUB,
        IdpProfile.PROVIDER_LDAP
    ],
    IdpProfile.PROVIDER_GOOGLE: [
        IdpProfile.PROVIDER_PASSWORDLESS,
        IdpProfile.PROVIDER_GOOGLE,
        IdpProfile.PROVIDER_GITHUB,
        IdpProfile.PROVIDER_LDAP
    ],
    IdpProfile.PROVIDER_GITHUB: [
        IdpProfile.PROVIDER_GITHUB,
        IdpProfile.PROVIDER_LDAP,
    ],
    IdpProfile.PROVIDER_LDAP: [
        IdpProfile.PROVIDER_LDAP
    ]
}


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

    def create_user(self, claims):
        user = super(MozilliansAuthBackend, self).create_user(claims)

        IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id=claims.get('user_id'),
            email=claims.get('email'),
            primary=True
        )

        return user

    def filter_users_by_claims(self, claims):
        """Override default method to store claims."""
        self.claims = claims
        users = super(MozilliansAuthBackend, self).filter_users_by_claims(claims)

        # Checking the primary email returned 0 users,
        # before creating a new user we should check if the identity returned exists
        if not users:
            idps = IdpProfile.objects.filter(auth0_user_id=claims.get('user_id'))
            user_ids = idps.values_list('profile__user__id', flat=True).distinct()
            return self.UserModel.objects.filter(id__in=user_ids)
        return users

    def check_authentication_method(self, user):
        """Check which Identity is used to login.

        This method, depending on the current status of the IdpProfile
        of a user, enforces MFA logins and creates the IdpProfiles.
        Returns the object (user) it was passed unchanged.
        """
        if not user:
            return None

        profile = user.userprofile
        auth0_user_id = self.claims.get('user_id')
        email = self.claims.get('email')

        # Get current_idp
        current_idp = get_object_or_none(IdpProfile, profile=profile, primary=True)

        # Get or create new `user_id`
        obj, _ = IdpProfile.objects.get_or_create(
            profile=profile,
            email=email,
            auth0_user_id=auth0_user_id)

        if current_idp:

            # Do not allow downgrades.
            if obj.type < current_idp.type:
                msg = u'Please use one of the following authentication methods: {}'
                # convert the tuple to a dict to easily get the values
                provider_types = dict(IdpProfile.PROVIDER_TYPES)
                methods = ', '.join(provider_types[x] for x in ALLOWED_IDP_FLOWS[current_idp.type])
                messages.error(self.request, msg.format(methods))
                return None

        # Mark other `user_id` as `primary=False`
        idp_q = IdpProfile.objects.filter(profile=profile)
        idp_q.exclude(auth0_user_id=auth0_user_id, email=email).update(primary=False)

        # Mark current `user_id` as `primary=True`
        idp_q.filter(auth0_user_id=auth0_user_id, email=email).update(primary=True)

        # Update CIS
        send_userprofile_to_cis.delay(profile.pk)
        return user

    def authenticate(self, **kwargs):
        """Override default method to add multiple Identity Profiles in an account."""
        user = super(MozilliansAuthBackend, self).authenticate(**kwargs)

        return self.check_authentication_method(user)
