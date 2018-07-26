import graphene
import requests

from django.conf import settings

from mozillians.graphql.schema import CoreProfile
from mozillians.graphql.utils import json2obj


class Query(object):
    """GraphQL Query class for the V2 Profiles."""

    profiles = graphene.List(CoreProfile, userId=graphene.String())

    def resolve_profiles(self, info, **kwargs):
        """GraphQL resolver for the profiles attribute."""
        resp = requests.get(settings.V2_PROFILE_ENDPOINT).json()

        data = json2obj(resp)
        # Query based on user_id
        user_id = kwargs.get('userId')
        if user_id:
            for profile in data:
                if profile['user_id']['value'] == user_id:
                    return [profile]
            return None
        return data
