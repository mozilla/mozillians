import graphene

from mozillians.graphql_profiles.schema import Profile, UserMenu
from mozillians.graphql_profiles.utils import retrieve_v2_profile


class Query(object):
    """GraphQL Query class for the V2 Profiles."""

    profile = graphene.Field(Profile, username=graphene.String())
    user_menu = graphene.Field(UserMenu)

    def resolve_profile(self, info, **kwargs):
        """GraphQL resolver for a single profile."""

        username_q = kwargs.get('username')
        profile_data = retrieve_v2_profile(info.context, username_q)
        # If we failed to find a profile, return an empty response
        if not profile_data:
            return None
        return profile_data

    def resolve_user_menu(self, info, **kwargs):
        profile_data = retrieve_v2_profile(info.context)
        # If we failed to find a profile, return an empty response
        if not profile_data:
            return None
        return profile_data
