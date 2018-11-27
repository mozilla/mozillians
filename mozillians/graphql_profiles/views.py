from django.conf import settings
from django.http import Http404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from csp.decorators import csp_exempt
from graphene_django.views import GraphQLView


class MozilliansGraphQLView(GraphQLView):
    """Class Based View to handle GraphQL requests."""

    @method_decorator(csrf_exempt)
    @method_decorator(csp_exempt)
    def dispatch(self, *args, **kwargs):
        """Override dispatch method to allow the use of multiple decorators."""

        if not settings.DINO_PARK_ACTIVE:
            raise Http404()

        return super(MozilliansGraphQLView, self).dispatch(*args, **kwargs)
