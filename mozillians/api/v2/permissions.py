from django.utils.timezone import now

import waffle
from django_statsd.clients import statsd
from rest_framework.permissions import BasePermission

from mozillians.api.models import APIv2App


class MozilliansPermission(BasePermission):
    def has_permission(self, request, view):
        if not waffle.flag_is_active(request, 'apiv2'):
            return False

        api_key = (request.REQUEST.get('api-key', None) or
                   request.META.get('HTTP_X_API_KEY', None))

        if api_key:
            try:
                app = APIv2App.objects.get(key=api_key, enabled=True)
            except APIv2App.DoesNotExist:
                statsd.incr('apiv2.auth.failed')
                return False

            request.privacy_level = app.privacy_level

            statsd.incr('apiv2.auth.success')
            statsd.incr('apiv2.requests.app.{0}'.format(app.id))
            statsd.incr('apiv2.requests.total')
            statsd.incr('apiv2.resources.{0}'.format(view.__class__.__name__))

            APIv2App.objects.filter(id=app.id).update(last_used=now())

            return True

        return False
