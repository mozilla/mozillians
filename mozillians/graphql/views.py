from django.views.decorators.csrf import csrf_exempt

from graphene_django.views import GraphQLView


class MozilliansGraphQLView(GraphQLView):
    """Class Based View to handle GraphQL requests."""

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        """Override dispatch method to allow the use of multiple decorators."""
        return super(MozilliansGraphQLView, self).dispatch(*args, **kwargs)
