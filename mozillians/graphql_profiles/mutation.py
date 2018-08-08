import json
import graphene
import requests

from django.conf import settings

from mozillians.graphql_profiles.schema import CoreProfile
from mozillians.graphql_profiles.utils import json2obj


class SimpleInputField(graphene.InputObjectType):
    """Simple Input Field that accepts a string argument."""
    value = graphene.String(required=False)


class BasicProfileInput(graphene.InputObjectType):
    """Basic Profile Mutation for the v2 profile schema."""
    first_name = graphene.InputField(SimpleInputField)
    last_name = graphene.InputField(SimpleInputField)
    primary_email = graphene.InputField(SimpleInputField)


class EditBasicProfile(graphene.Mutation):

    class Arguments:
        basic_profile_data = BasicProfileInput(required=False)
        # Get the user_id for editing
        user_id = graphene.String(required=True)

    errors = graphene.List(graphene.String)
    updated_profile = graphene.Field(lambda: CoreProfile)

    @staticmethod
    def mutate(root, info, user_id, basic_profile_data=None):
        """Update the Basic information of a Profile."""

        resp = requests.get(settings.V2_PROFILE_ENDPOINT).json()

        data = json2obj(json.dumps(resp))
        for profile in data:
            # Get the profile with the specific userId
            if profile['user_id']['value'] == user_id:
                # Update the profile only if we have new data
                if basic_profile_data:
                    for k, v in basic_profile_data.items():
                        profile[k].update(v)
                return EditBasicProfile(updated_profile=profile)
        return None
