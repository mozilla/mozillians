import base64
import hashlib
import json
import re

from django.db import transaction
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User

from cities_light.models import Country
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from waffle import switch_is_active

from mozillians.common.templatetags.helpers import get_object_or_none
from mozillians.dino_park.utils import _dino_park_get_profile_by_userid
from mozillians.users.models import IdpProfile
from mozillians.users.tasks import send_userprofile_to_cis


# Only allow the following login flows
# Passwordless > Google > Github, FxA > LDAP
# There is no way to downgrade
ALLOWED_IDP_FLOWS = {
    IdpProfile.PROVIDER_PASSWORDLESS: IdpProfile.MFA_ACCOUNTS + [
        IdpProfile.PROVIDER_PASSWORDLESS,
        IdpProfile.PROVIDER_GOOGLE,
    ],
    IdpProfile.PROVIDER_GOOGLE: IdpProfile.MFA_ACCOUNTS + [
        IdpProfile.PROVIDER_PASSWORDLESS,
        IdpProfile.PROVIDER_GOOGLE,
    ],
    IdpProfile.PROVIDER_GITHUB: IdpProfile.MFA_ACCOUNTS,
    IdpProfile.PROVIDER_FIREFOX_ACCOUNTS: IdpProfile.MFA_ACCOUNTS,
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

    def create_mozillians_profile(self, user_id, idp):
        # A new mozillians.org profile will be provisioned if there is not one,
        # we need the self-view of profile which mean a private scope
        # Because we are using OIDC proxy, we assume always ldap. This functionality
        # will be deprecated with the launch of DinoPark

        profile = idp.profile
        v2_profile_data = _dino_park_get_profile_by_userid(user_id)
        if not v2_profile_data:
            full_name = 'Anonymous Mozillian'
        else:
            try:
                data = json.loads(v2_profile_data)
            except (TypeError, ValueError):
                data = v2_profile_data
            # Escape the middleware
            first_name = data.get('first_name', {}).get('value')
            last_name = data.get('last_name', {}).get('value')
            full_name = first_name + ' ' + last_name
            # TODO: Update this. It's wrong to create entries like this. We need to populate
            # the Country table and match the incoming location. It's only for M1 beta.
            location = data.get('location_preference', {}).get('value')
            if location:
                country, _ = Country.objects.get_or_create(name=location)
                profile.country = country
            timezone = data.get('timezone', {}).get('value')
            if timezone:
                profile.timezone = timezone
            profile.title = data.get('fun_title', {}).get('value', '')
            worker_type = data.get('worker_type', {}).get('value')
            if worker_type:
                profile.is_staff = True
        profile.full_name = full_name
        profile.auth0_user_id = user_id
        profile.save()
        if profile.is_staff:
            profile.auto_vouch()

    def get_or_create_user(self, *args, **kwargs):
        user = super(MozilliansAuthBackend, self).get_or_create_user(*args, **kwargs)
        if switch_is_active('dino-park-autologin') and user:
            self.request.session['oidc_login_next'] = '/beta'

        return user

    def get_username(self, claims):
        """This method is mostly useful when it is used in DinoPark.

        If we are creating a user and the Search Service already has a username,
        we will use that. Otherwise, we will get the username derived from username_algo.
        """
        username = super(MozilliansAuthBackend, self).get_username(claims)

        if switch_is_active('dino-park-autologin'):
            auth0_user_id = claims.get('user_id') or claims.get('sub')
            v2_username = _dino_park_get_profile_by_userid(auth0_user_id, return_username=True)
            if v2_username and username != v2_username:
                return v2_username
        return username

    def create_user(self, claims):
        user = super(MozilliansAuthBackend, self).create_user(claims)
        # Ensure compatibility with OIDC conformant mode
        auth0_user_id = claims.get('user_id') or claims.get('sub')

        idp = IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id=auth0_user_id,
            email=claims.get('email'),
            primary=True
        )
        # This is temporary for the beta version of DinoPark.
        # and will be removed after that.
        if switch_is_active('dino-park-autologin'):
            self.create_mozillians_profile(auth0_user_id, idp)

        return user

    def filter_users_by_claims(self, claims):
        """Override default method to store claims."""
        self.claims = claims
        users = super(MozilliansAuthBackend, self).filter_users_by_claims(claims)

        # Checking the primary email returned 0 users,
        # before creating a new user we should check if the identity returned exists
        if not users:
            # Ensure compatibility with OIDC conformant mode
            auth0_user_id = claims.get('user_id') or claims.get('sub')
            idps = IdpProfile.objects.filter(auth0_user_id=auth0_user_id)
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
        # Ensure compatibility with OIDC conformant mode
        auth0_user_id = self.claims.get('user_id') or self.claims.get('sub')
        email = self.claims.get('email')
        # Grant an employee vouch if the user has the 'hris_is_staff' group
        groups = self.claims.get('https://sso.mozilla.com/claim/groups')
        if groups and 'hris_is_staff' in groups:
            profile.auto_vouch()

        # Get current_idp
        current_idp = get_object_or_none(IdpProfile, profile=profile, primary=True)

        # Get or create new `user_id`
        obj, _ = IdpProfile.objects.get_or_create(
            profile=profile,
            email=email,
            auth0_user_id=auth0_user_id)

        # Update/Save the Github username
        if 'github|' in auth0_user_id:
            obj.username = self.claims.get('nickname', '')
            obj.save()

        # Do not allow downgrades.
        if current_idp and obj.type < current_idp.type:
            msg = u'Please use {0} as the login method to authenticate'
            messages.error(self.request, msg.format(current_idp.get_type_display()))
            return None

        # Mark other `user_id` as `primary=False`
        idp_q = IdpProfile.objects.filter(profile=profile)
        with transaction.atomic():
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
