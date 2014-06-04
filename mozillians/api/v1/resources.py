from django.utils.cache import patch_cache_control

from django_statsd.clients import statsd


class ClientCacheResourceMixIn(object):
    """
    Mixin class which sets Cache-Control headers on API responses
    using a ``cache_control`` dictionary from the resource's Meta
    class.

    TODO: To be removed when we upgrade to django-tastypie >= 0.9.12.

    Code from http://django-tastypie.readthedocs.org/en/latest/caching.html
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


class GraphiteMixIn(object):
    """
    MixIn to post to graphite server every hit of API resource.
    """

    def wrap_view(self, view):
        real_wrapper = super(GraphiteMixIn, self).wrap_view(view)

        def wrapper(request, *args, **kwargs):
            callback = getattr(self, view)
            counter_name = 'api.resources.{klass}.{func}'.format(
                klass=callback.im_class.__name__,
                func=callback.im_func.__name__)
            statsd.incr(counter_name)
            return real_wrapper(request, *args, **kwargs)
        return wrapper
