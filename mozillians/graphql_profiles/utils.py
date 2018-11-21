import json
from aniso8601 import parse_datetime

from django.contrib.auth.models import User

from mozillians.common.templatetags.helpers import get_object_or_none
from mozillians.dino_park.views import orgchart_get_by_username, search_get_profile
from mozillians.dino_park.utils import UserAccessLevel


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


def json2obj(payload):
    """Return a Python object from json."""
    try:
        data = json.loads(payload, object_hook=object_hook)
    except ValueError:
        data = None
    return data


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


def retrieve_v2_profile(request, username=None, from_db=False):
    """Helper method to retrieve a profile either from the v2 schema or
    from the database.
    """

    if not username and not request.user.is_authenticated():
        return None
    username_q = username or request.user.username

    if from_db:
        # This is a db query, let's return the user
        profile = get_object_or_none(User, username=username_q)
        return profile

    # We need to fetch data from ES
    orgchart_related_data = None
    if not username:
        # This is a query to get a minified version of a profile
        # for the user menu
        profile_data = search_get_profile(request, username_q, UserAccessLevel.PRIVATE)
    else:
        profile_data = search_get_profile(request, username_q)
        orgchart_related_data = orgchart_get_by_username(request, 'related', username_q)

    profile = json2obj(profile_data.content)
    if orgchart_related_data:
        profile.update(json2obj(orgchart_related_data.content))

    return profile
