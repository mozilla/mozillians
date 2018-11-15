import json
from aniso8601 import parse_datetime

from mozillians.common.templatetags.helpers import get_object_or_none
from mozillians.dino_park.views import orgchart_get_by_id, search_get_profile
from mozillians.users.models import UserProfile


class ProfileFactory(dict):
    """Allows to parse a dict structure with an object like notation (attributes)."""

    def __init__(self, data={}):
        super(ProfileFactory, self).__init__()
        for k, v in data.items():
            self.__setitem__(k, v)

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            value = ProfileFactory(value)
        super(ProfileFactory, self).__setitem__(key, value)

    def __getattr__(self, item):
        try:
            return self.__getitem__(item)
        except KeyError:
            raise AttributeError(item)

    __setattr__ = __setitem__


def object_hook(dct):
    """Transform every JSON object to Python objects."""
    return ProfileFactory(dct)


def json2obj(data):
    """Return a Python object from json."""
    return json.loads(data, object_hook=object_hook)


def parse_datetime_iso8601(datetime):
    """Parse a string in ISO8601 format."""
    if not datetime:
        return None

    try:
        dt = parse_datetime(datetime)
    except ValueError:
        return None
    else:
        return dt


def retrieve_v2_profile(request, user_id, from_db=False):
    """Helper method to retrieve a profile either from the v2 schema or
    from the database.
    """
    profile_auth0_id = None
    if request.user.is_authenticated():
        profile_auth0_id = request.user.userprofile.auth0_user_id
    user_id = user_id or profile_auth0_id
    if not user_id:
        return None

    if from_db:
        profile = get_object_or_none(UserProfile, auth0_user_id=user_id)
    else:
        # We need to fetch data from ES
        profile_data = search_get_profile(request, user_id)
        orgchart_related_data = orgchart_get_by_id(request, 'related', user_id)

        profile = json2obj(profile_data.content)
        profile.update(json2obj(orgchart_related_data.content))

    return profile
