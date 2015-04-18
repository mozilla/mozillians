from django_statsd.clients import statsd

from tastypie.authentication import Authentication

from mozillians.api.models import APIApp


class AppAuthentication(Authentication):
    """App Authentication."""

    def is_authenticated(self, request, **kwargs):
        """Authenticate and authorize App."""
        app_key = request.GET.get('app_key', '')
        app_name = request.GET.get('app_name', '')

        try:
            app = APIApp.objects.get(name__iexact=app_name, key=app_key, is_active=True)
        except APIApp.DoesNotExist:
            statsd.incr('api.auth.failed')
            return False

        statsd.incr('api.auth.success')
        if not app.is_mozilla_app:
            statsd.incr('api.requests.total_community')
            data = request.GET.copy()
            data['restricted'] = True
            request.GET = data
        else:
            statsd.incr('api.requests.total_mozilla')
        return True
