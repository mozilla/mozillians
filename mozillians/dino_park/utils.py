import requests
import urlparse

from django.conf import settings
from django.http import JsonResponse


def _dino_park_get_profile_by_userid(user_id, return_username=False):
    """This is a method that queries the Search Service (ES).

    Querying by user_id, ES returns a full profile. This call uses
    an `internal` url that should not be used to query profiles.
    It is reserved for internal usage, mainly to create new profiles in
    DinoPark from an Auth0 ID or to retrieve the username when it is not known.
    """

    if not user_id:
        return None

    url_parts = urlparse.ParseResult(
        scheme='http',
        netloc=settings.DINO_PARK_SEARCH_SVC,
        path='/search/getByUserId/{}'.format(user_id),
        params='',
        query='',
        fragment=''
    )
    url = urlparse.urlunparse(url_parts)
    resp = requests.get(url)
    try:
        resp.raise_for_status()
    except requests.exceptions.HTTPError:
        return None

    data = resp.json()

    # If this flag is set, return only the username of the user
    if return_username:
        return data.get('usernames', {}).get('values', {}).get('mozilliansorg', '')
    return data


class UserAccessLevel(object):
    """Class to handle privacy related scopes in DinoPark."""
    # Privacy classifications for Dino Park
    PRIVATE = 'private'
    STAFF = 'staff'
    NDA = 'nda'
    VOUCHED = 'vouched'
    AUTHENTICATED = 'authenticated'
    PUBLIC = 'public'

    @classmethod
    def get_privacy(cls, request, user=None):
        """Return user privacy clearance for Dino Park."""
        request_user = request.user

        if request_user.is_authenticated():
            # The order here is important. Private has the highest access of all and
            # public the least.
            # Admins (superusers) have PRIVATE access. This is matching functionality from
            # current mozillians.org
            if (request_user.is_superuser or (user and user == request_user)):
                return cls.PRIVATE
            if request_user.userprofile.is_staff:
                return cls.STAFF
            if request_user.userprofile.is_nda:
                return cls.NDA
            if request_user.userprofile.is_vouched:
                return cls.VOUCHED
            # If we did not match all the above cases, return an authenticated user
            return cls.AUTHENTICATED
        return cls.PUBLIC


class DinoErrorResponse(object):
    """Error codes to return in DinoPark."""

    PERMISSION_ERROR = 'Permission Denied: Scope mismatch.'

    @classmethod
    def get_error(cls, msg, status_code=403):
        errors = {
            'error': msg
        }
        return JsonResponse(data=errors, status=status_code)
