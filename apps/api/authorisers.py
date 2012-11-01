from tastypie.authorization import ReadOnlyAuthorization

from models import APIApp


class MozillaOfficialAuthorization(ReadOnlyAuthorization):
    """Authorize an App as official Mozilla or Community."""

    def is_authorized(self, request, object=None):
        """Authorize App.

        Always authorize Apps. Community Apps get a 'restricted' URL
        parameter.

        """
        app_name = request.GET.get('app_name', None)
        app_key = request.GET.get('app_key', None)
        app = APIApp.objects.get(name=app_name, key=app_key)

        if not app.is_mozilla_app:
            data = request.GET.copy()
            data['restricted'] = True
            request.GET = data
        return True
