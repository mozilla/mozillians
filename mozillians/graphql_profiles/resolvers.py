from mozillians.graphql_profiles.utils import parse_datetime_iso8601


DATETIME_ATTRS = ['created', 'last_modified']


def dino_park_resolver(attname, default_value, root, info, *args):
    """Custom resolver for all the attributes in a profile.
    """

    profile_attr = root.get(attname, default_value)
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
