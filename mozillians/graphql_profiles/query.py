import graphene

from mozillians.common.templatetags.helpers import get_object_or_none
from mozillians.dino_park.views import orgchart_get_related, search_get_profile
from mozillians.graphql_profiles.schema import Profile, Vouches
from mozillians.graphql_profiles.utils import json2obj
from mozillians.users.models import UserProfile, Vouch


def _retrieve_profile(request, user_id, from_db=False):
    """Helper method to retrieve a profile either from the v2 schema or
    from the database.
    """
    profile_auth0_id = None
    if request.user.is_authenticated():
        profile_auth0_id = request.user.userprofile.auth0_user_id
    user_id = user_id or profile_auth0_id
    if not user_id:
        return None

    if from_db:
        profile = get_object_or_none(UserProfile, user_id=user_id)
    else:
        # We need to fetch data from ES
        profile_data = search_get_profile(request, user_id)
        orgchart_related_data = orgchart_get_related(request, user_id)

        profile = json2obj(profile_data.content)
        profile.update(json2obj(orgchart_related_data.content))

    return profile


class Query(object):
    """GraphQL Query class for the V2 Profiles."""

    profile = graphene.Field(Profile, userId=graphene.String())
    vouches = graphene.List(Vouches, userId=graphene.String())

    def resolve_profile(self, info, **kwargs):
        """GraphQL resolver for a single profile."""

        user_id = kwargs.get('userId')
        profile_data = _retrieve_profile(info.context, user_id)
        # If we failed to find a profile, return an empty response
        if not profile_data:
            return None
        return profile_data

    def resolve_vouches(self, info, **kwargs):
        user_id = kwargs.get('userId')
        profile = self._retrieve_profile(info.context, user_id, from_db=True)
        if not profile:
            return None
        return Vouch.objects.filter(vouchee=profile)
