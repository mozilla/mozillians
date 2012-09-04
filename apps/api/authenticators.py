from tastypie.authentication import Authentication

from models import APIApp


class AppAuthentication(Authentication):
    """App Authentication."""

    def is_authenticated(self, request, **kwargs):
        """Authenticate App."""
        app_key = request.GET.get('app_key', None)
        app_name = request.GET.get('app_name', None)

        return (APIApp.objects.filter(name__iexact=app_name, key=app_key,
                                      is_active=True).exists())

