import json
from aniso8601 import parse_datetime


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
