import re
import urllib
from contextlib import contextmanager
from warnings import warn

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponsePermanentRedirect
from django.utils.encoding import iri_to_uri, smart_str

from django.utils.translation import ugettext_lazy as _lazy, activate

from mozillians.common import urlresolvers
from mozillians.common.templatetags.helpers import redirect, urlparams
from mozillians.common.urlresolvers import reverse


LOGIN_MESSAGE = _lazy(u'You must be logged in to continue.')
GET_VOUCHED_MESSAGE = _lazy(u'You must be vouched to continue.')


class StrongholdMiddleware(object):
    """Keep unvouched users out, unless explicitly allowed in.

    Inspired by https://github.com/mgrouchy/django-stronghold/

    """

    def __init__(self):
        self.exceptions = getattr(settings, 'STRONGHOLD_EXCEPTIONS', [])

    def process_view(self, request, view_func, view_args, view_kwargs):
        for view_url in self.exceptions:
            if re.match(view_url, request.path):
                return None

        allow_public = getattr(view_func, '_allow_public', None)
        if allow_public:
            return None

        if not request.user.is_authenticated():
            messages.warning(request, LOGIN_MESSAGE)
            return (login_required(view_func, login_url=reverse('phonebook:home'))
                    (request, *view_args, **view_kwargs))

        if request.user.userprofile.is_vouched:
            return None

        allow_unvouched = getattr(view_func, '_allow_unvouched', None)
        if allow_unvouched:
            return None

        messages.error(request, GET_VOUCHED_MESSAGE)
        return redirect('phonebook:home')


@contextmanager
def safe_query_string(request):
    """Turn the QUERY_STRING into a unicode- and ascii-safe string.

    We need unicode so it can be combined with a reversed URL, but it
    has to be ascii to go in a Location header. iri_to_uri seems like
    a good compromise.
    """
    qs = request.META['QUERY_STRING']
    try:
        request.META['QUERY_STRING'] = iri_to_uri(qs)
        yield
    finally:
        request.META['QUERY_STRING'] = qs


class LocaleURLMiddleware(object):
    """
    1. Search for the locale.
    2. Save it in the request.
    3. Strip them from the URL.
    """

    def __init__(self):
        if not settings.USE_I18N or not settings.USE_L10N:
            warn("USE_I18N or USE_L10N is False but LocaleURLMiddleware is "
                 "loaded. Consider removing funfactory.middleware."
                 "LocaleURLMiddleware from your MIDDLEWARE_CLASSES setting.")

    def _is_lang_change(self, request):
        """Return True if the lang param is present and URL isn't exempt."""
        if 'lang' not in request.GET:
            return False

    def process_request(self, request):

        # Don't apply middleware to requests matching exempt URLs
        # Use default LANGUAGE_CODE locale
        for view_url in settings.EXEMPT_L10N_URLS:
            if re.match(view_url, request.path):
                request.locale = settings.LANGUAGE_CODE
                activate(settings.LANGUAGE_CODE)
                return None

        prefixer = urlresolvers.Prefixer(request)
        urlresolvers.set_url_prefix(prefixer)
        full_path = prefixer.fix(prefixer.shortened_path)

        if self._is_lang_change(request):
            # Blank out the locale so that we can set a new one. Remove lang
            # from the query params so we don't have an infinite loop.
            prefixer.locale = ''
            new_path = prefixer.fix(prefixer.shortened_path)
            query = dict((smart_str(k), request.GET[k]) for k in request.GET)
            query.pop('lang')
            return HttpResponsePermanentRedirect(urlparams(new_path, **query))

        if full_path != request.path:
            query_string = request.META.get('QUERY_STRING', '')
            full_path = urllib.quote(full_path.encode('utf-8'))

            if query_string:
                full_path = '%s?%s' % (full_path, query_string)

            response = HttpResponsePermanentRedirect(full_path)

            # Vary on Accept-Language if we changed the locale
            old_locale = prefixer.locale
            new_locale, _ = urlresolvers.split_path(full_path)
            if old_locale != new_locale:
                response['Vary'] = 'Accept-Language'

            return response

        request.path_info = '/' + prefixer.shortened_path
        request.locale = prefixer.locale or settings.LANGUAGE_CODE
        activate(prefixer.locale or settings.LANGUAGE_CODE)
