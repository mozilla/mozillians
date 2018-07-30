from django.http import Http404
from django.views.decorators.csrf import csrf_exempt

import waffle
from graphene_django.views import GraphQLView


class MozilliansGraphQLView(GraphQLView):
    """Class Based View to handle GraphQL requests."""

    @csrf_exempt
    def dispatch(self, *args, **kwargs):
        """Override dispatch method to allow the use of multiple decorators."""
        if not waffle.flag_is_active(self.request, 'enable_graphql'):
            raise Http404()
        return super(MozilliansGraphQLView, self).dispatch(*args, **kwargs)
