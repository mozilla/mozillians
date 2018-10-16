from django.http import Http404
from django.utils.decorators import method_decorator

import waffle
from csp.decorators import csp_exempt
from graphene_django.views import GraphQLView
from session_csrf import anonymous_csrf_exempt


class MozilliansGraphQLView(GraphQLView):
    """Class Based View to handle GraphQL requests."""

    @method_decorator(anonymous_csrf_exempt)
    @method_decorator(csp_exempt)
    def dispatch(self, *args, **kwargs):
        """Override dispatch method to allow the use of multiple decorators."""

        if not waffle.flag_is_active(self.request, 'enable_graphql'):
            raise Http404()

        return super(MozilliansGraphQLView, self).dispatch(*args, **kwargs)
