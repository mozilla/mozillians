from django.http import (HttpResponseForbidden, HttpResponseNotAllowed,
                         HttpResponseRedirect)

from funfactory.urlresolvers import reverse

from mozillians.urls import error_page


class PermissionDeniedMiddleware(object):
    """Add a generic 40x "not allowed" handler.

    Currently throws a 500 error, but in the future should display a
    more tailored "not allowed" page."""
    def process_response(self, request, response):
        if isinstance(response, (HttpResponseForbidden,
                                 HttpResponseNotAllowed)):
            if request.user.is_authenticated():
                    return error_page(request, 500,
                                      status=response.status_code)
            else:
                return HttpResponseRedirect(reverse('login'))

        return response
