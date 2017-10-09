import base64
import hashlib
import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q

from mozilla_django_oidc.auth import OIDCAuthenticationBackend

from mozillians.common.templatetags.helpers import get_object_or_none
from mozillians.users.models import ExternalAccount, IdpProfile
from mozillians.users.tasks import send_userprofile_to_cis


# Only allow the following login flows
# Passwordless > Google > Github > LDAP
# There is no way to downgrade
ALLOWED_IDP_FLOWS = {
    IdpProfile.PROVIDER_PASSWORDLESS: [
        IdpProfile.PROVIDER_PASSWORDLESS,
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
            profile=self.request.user.userprofile,
            auth0_user_id=claims.get('user_id'),
            primary=True
        )

        return user

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

        # Allow logins only using primary email
        user_q = self.UserModel.objects.filter(email=email)

        if user_q.exists():
            # Get or create an IdpProfile for this user
            profile = user_q[0].userprofile
            auth0_user_id = claims.get('user_id')

            # Get current_idp
            current_idp = get_object_or_none(IdpProfile, profile=profile, primary=True)

            # Get or create new `user_id`
            obj, _ = IdpProfile.objects.get_or_create(
                profile=profile,
                auth0_user_id=auth0_user_id)

            if current_idp:

                if obj.type not in ALLOWED_IDP_FLOWS[current_idp.type]:
                    msg = u'Please use one of the following authentication methods: {}'
                    methods = ', '.join(ALLOWED_IDP_FLOWS[current_idp.type])
                    messages.error(self.request, msg.format(methods))
                    return self.UserModel.objects.none()

            # Mark other `user_id` as `primary=False`
            idp_q = IdpProfile.objects.filter(profile=profile)
            idp_q.exclude(auth0_user_id=auth0_user_id).update(primary=False)

            # Mark current `user_id` as `primary=True`
            idp_q.filter(auth0_user_id=auth0_user_id).update(primary=True)

            # Update CIS
            send_userprofile_to_cis.delay(profile.pk)

        # Add alternate email
        if request_user.is_authenticated():
            email_q = self.UserModel.objects.filter(primary_email_qs | alternate_email_qs)

            if not email_q:
                # In this case we have a registered user who is adding a secondary email
                ExternalAccount.objects.create(type=account_type,
                                               user=request_user.userprofile,
                                               identifier=email)
            else:
                if not user_q.filter(pk=request_user.id).exists():
                    msg = u'Email {0} already exists in the database.'.format(email)
                    messages.error(self.request, msg)
            return [request_user]

        return user_q
