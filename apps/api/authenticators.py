from django_statsd.clients import statsd
from tastypie.authentication import Authentication

from models import APIApp


class AppAuthentication(Authentication):
    """App Authentication."""

    def is_authenticated(self, request, **kwargs):
        """Authenticate App."""
        app_key = request.GET.get('app_key', '')
        app_name = request.GET.get('app_name', '')

        result = (APIApp.objects.filter(name__iexact=app_name, key=app_key,
                                       is_active=True).exists())
        if result:
            statsd.incr('api.auth.success')
        else:
            statsd.incr('api.auth.failed')

        return result
