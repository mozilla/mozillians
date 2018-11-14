import graphene

from mozillians.graphql_profiles.schema import Profile
from mozillians.graphql_profiles.utils import retrieve_v2_profile


class Query(object):
    """GraphQL Query class for the V2 Profiles."""

    profile = graphene.Field(Profile, userId=graphene.String())

    def resolve_profile(self, info, **kwargs):
        """GraphQL resolver for a single profile."""

        user_id = kwargs.get('userId')
        profile_data = retrieve_v2_profile(info.context, user_id)
        # If we failed to find a profile, return an empty response
        if not profile_data:
            return None
        return profile_data
