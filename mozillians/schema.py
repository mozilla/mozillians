import graphene

from mozillians.graphql_profiles import query


class Query(query.Query, graphene.ObjectType):
    """Top level Query.

    This class inherits from multiple queries throughout the project.
    """
    pass


schema = graphene.Schema(query=Query) # noqa
