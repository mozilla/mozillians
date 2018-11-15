from mozillians.graphql_profiles.utils import parse_datetime_iso8601, retrieve_v2_profile
from mozillians.users.models import Vouch


DATETIME_ATTRS = ['created', 'last_modified']


def dino_park_resolver(attname, default_value, root, info, *args):
    """Custom resolver for all the attributes in a profile."""

    profile_attr = root.get(attname, default_value)

    # If we don't get a profile attribute back, probably it's a query from a different
    # source than the v2 profile. Let's try to resolve this from the mozillians db.
    if not profile_attr:
        username = root.get('usernames', {}).get('values', {}).get('mozilliansorg', default_value)
        # We missed that too. Just return root back
        if not username:
            return root

        # Top level username in GraphQL. We have one, let's return it
        if attname == 'username':
            return username
        profile = retrieve_v2_profile(info.context, username, from_db=True)

        # We are looking for vouches! Let's return a few
        if attname == 'vouches':
            return Vouch.objects.filter(vouchee=profile)
        return profile

    if profile_attr and hasattr(profile_attr, 'get'):
        # Get either the value or values from the v2 schema and return them
        # This allows us to avoid one level of nesting in our responses
        value = profile_attr.get('value') or profile_attr.get('values')
        # If we don't have a value/values attrs and it is a dict then we
        # have nested attributes. Let's return them so that nested resolvers
        # can do the matching
        if not value:
            return profile_attr
        # If we are here, we already have a match. Let's check if it's of DateTime type
        if attname in DATETIME_ATTRS:
            return parse_datetime_iso8601(value)

        return value
    return profile_attr
