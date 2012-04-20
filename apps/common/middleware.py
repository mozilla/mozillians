import os
from contextlib import contextmanager

from django.http import (HttpResponseForbidden, HttpResponseNotAllowed,
                         HttpResponseRedirect, HttpResponsePermanentRedirect)
from django.middleware import common
from django.utils.encoding import iri_to_uri

import commonware.log
from funfactory.manage import ROOT
from funfactory.urlresolvers import reverse

# TODO: this is hackish. Once we update mozillians to the newest playdoh layout
error_page = __import__('%s.urls' % os.path.basename(ROOT)).urls.error_page
log = commonware.log.getLogger('m.phonebook')


class PermissionDeniedMiddleware(object):
    """Add a generic 40x "not allowed" handler.

    TODO: Currently uses the 500.html error template, but in the future should
    display a more tailored-to-the-actual-error "not allowed" page."""
    def process_response(self, request, response):
        if isinstance(response, (HttpResponseForbidden,
                                 HttpResponseNotAllowed)):
            if request.user.is_authenticated():
                log.debug('Permission denied middleware, user was '
                         'authenticated, sending 500')
                return error_page(request, 500, status=response.status_code)
            else:
                if isinstance(response, (HttpResponseForbidden)):
                    log.debug('Response was forbidden')
                elif isinstance(response, (HttpResponseNotAllowed)):
                    log.debug('Response was not allowed')
                log.debug('Permission denied middleware, redirecting home')
                return HttpResponseRedirect(reverse('home'))
        return response


class RemoveSlashMiddleware(object):
    """
    Middleware that tries to remove a trailing slash if there was a 404.

    If the response is a 404 because url resolution failed, we'll look for a
    better url without a trailing slash.

    Cribbed from kitsune:
    https://github.com/mozilla/kitsune/blob/master/apps/sumo/middleware.py
    """

    def process_response(self, request, response):
        if (response.status_code == 404
            and request.path_info.endswith('/')
            and not common._is_valid_path(request.path_info)
            and common._is_valid_path(request.path_info[:-1])):
            # Use request.path because we munged app/locale in path_info.
            newurl = request.path[:-1]
            if request.GET:
                with safe_query_string(request):
                    newurl += '?' + request.META['QUERY_STRING']
            return HttpResponsePermanentRedirect(newurl)
        return response


@contextmanager
def safe_query_string(request):
    """
    Turn the QUERY_STRING into a unicode- and ascii-safe string.

    We need unicode so it can be combined with a reversed URL, but it has to be
    ascii to go in a Location header. iri_to_uri seems like a good compromise.
    """
    qs = request.META['QUERY_STRING']
    try:
        request.META['QUERY_STRING'] = iri_to_uri(qs)
        yield
    finally:
        request.META['QUERY_STRING'] = qs
