from django.utils.timezone import now

from rest_framework.permissions import BasePermission

from mozillians.api.models import APIv2App


class MozilliansPermission(BasePermission):
    def has_permission(self, request, view):
        api_key = None

        if request.user.is_authenticated():
            api_query = APIv2App.objects.filter(owner=request.user.userprofile)
            if api_query.exists():
                api_key = api_query.order_by('privacy_level')[0].key

        api_key = (request.GET.get('api-key') or request.META.get('HTTP_X_API_KEY') or api_key)

        if api_key:
            try:
                app = APIv2App.objects.get(key=api_key, enabled=True)
            except APIv2App.DoesNotExist:
                return False

            request.privacy_level = app.privacy_level

            APIv2App.objects.filter(id=app.id).update(last_used=now())

            return True
        return False
