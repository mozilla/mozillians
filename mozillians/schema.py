import graphene

from mozillians.graphql_profiles import query
from mozillians.graphql_profiles.mutation import EditBasicProfile


class Query(query.Query, graphene.ObjectType):
    """Top level Query.

    This class inherits from multiple queries throughout the project.
    """
    pass


class ProfileMutations(graphene.ObjectType):
    edit_basic_profile = EditBasicProfile.Field()

schema = graphene.Schema(query=Query, mutation=ProfileMutations) # noqa
