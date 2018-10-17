import json
import graphene

from mozillians.dino_park.views import search_get_profile
from mozillians.graphql_profiles.schema import CoreProfile, Vouches
from mozillians.graphql_profiles.utils import json2obj
from mozillians.users.models import Vouch


class Query(object):
    """GraphQL Query class for the V2 Profiles."""

    profile = graphene.Field(CoreProfile, userId=graphene.String(required=True))
    vouches = graphene.List(Vouches, userId=graphene.String(required=True))

    def resolve_profile(self, info, **kwargs):
        """GraphQL resolver for a single profile."""

        user_id = kwargs.get('userId')
        v2_profile_data = search_get_profile(info.context, user_id)

        data = json2obj(json.dumps(v2_profile_data))
        for profile in data:
            if profile['user_id']['value'] == user_id:
                return profile
        return None

    def resolve_vouches(self, info, **kwargs):
        user_id = kwargs.get('userId')
        if not user_id:
            return None
        return Vouch.objects.filter(vouchee__auth0_user_id=user_id)
