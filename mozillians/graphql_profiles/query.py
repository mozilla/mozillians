import json
import graphene
import requests

from django.conf import settings

from mozillians.graphql_profiles.schema import CoreProfile, Vouches
from mozillians.graphql_profiles.utils import json2obj
from mozillians.users.models import Vouch


class Query(object):
    """GraphQL Query class for the V2 Profiles."""

    profiles = graphene.List(CoreProfile)
    profile = graphene.Field(CoreProfile, userId=graphene.String(required=True))
    vouches = graphene.List(Vouches, userId=graphene.String(required=True))

    def resolve_profiles(self, info, **kwargs):
        """GraphQL resolver for the profiles attribute."""
        resp = requests.get(settings.V2_PROFILE_ENDPOINT).json()

        return json2obj(json.dumps(resp))

    def resolve_profile(self, info, **kwargs):
        """GraphQL resolver for a single profile."""

        resp = requests.get(settings.V2_PROFILE_ENDPOINT).json()

        data = json2obj(json.dumps(resp))
        user_id = kwargs.get('userId')
        for profile in data:
            if profile['user_id']['value'] == user_id:
                return profile
        return None

    def resolve_vouches(self, info, **kwargs):
        user_id = kwargs.get('userId')
        if not user_id:
            return None
        return Vouch.objects.filter(vouchee__auth0_user_id=user_id)
