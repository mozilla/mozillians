import graphene

from mozillians.dino_park.views import orgchart_get_related, search_get_profile
from mozillians.graphql_profiles.schema import Profile, Vouches
from mozillians.graphql_profiles.utils import json2obj
from mozillians.users.models import Vouch


class Query(object):
    """GraphQL Query class for the V2 Profiles."""

    profile = graphene.Field(Profile, userId=graphene.String(required=True))
    vouches = graphene.List(Vouches, userId=graphene.String(required=True))

    def resolve_profile(self, info, **kwargs):
        """GraphQL resolver for a single profile."""

        user_id = kwargs.get('userId')
        v2_profile_data = search_get_profile(info.context, user_id)
        orgchart_related_data = orgchart_get_related(info.context, user_id)

        data = json2obj(v2_profile_data.content)
        data.update(json2obj(orgchart_related_data.content))
        return data

    def resolve_vouches(self, info, **kwargs):
        user_id = kwargs.get('userId')
        if not user_id:
            return None
        return Vouch.objects.filter(vouchee__auth0_user_id=user_id)
