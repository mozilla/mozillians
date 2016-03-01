from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

from rest_framework.viewsets import ReadOnlyModelViewSet


class NoCacheReadOnlyModelViewSet(ReadOnlyModelViewSet):
    """DRF ReadOnlyModelViewSet with non-cached responses."""

    @method_decorator(never_cache)
    def dispatch(self, *args, **kwargs):
        return super(NoCacheReadOnlyModelViewSet, self).dispatch(*args, **kwargs)
