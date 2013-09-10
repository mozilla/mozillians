# Implement HTTP Caching
# code from http://django-tastypie.readthedocs.org/en/latest/caching.html
from django.utils.cache import patch_cache_control


class ClientCacheResourceMixIn(object):
    """
    Mixin class which sets Cache-Control headers on API responses
    using a ``cache_control`` dictionary from the resource's Meta
    class.

    TODO: To be removed when we upgrade to django-tastypie >= 0.9.12.

    """

    def create_response(self, request, data, **response_kwargs):
        response = (super(ClientCacheResourceMixIn, self)
                    .create_response(request, data, **response_kwargs))

        if (request.method == 'GET' and response.status_code == 200
            and hasattr(self.Meta, 'cache_control')):
            patch_cache_control(response, **self.Meta.cache_control)

        return response


class AdvancedSortingResourceMixIn(object):
    """
    MixIn to allow sorting on multiple values in the same query.
    """

    def apply_sorting(self, obj_list, options=None):
        """Allow sorting on multiple values. """
        sort_list = [order_value for order_value
                     in options.get('order_by', '').split(',')
                     if order_value.strip('-') in self.Meta.ordering]

        if not sort_list:
            sort_list = self.Meta.default_order

        return obj_list.order_by(*sort_list)
