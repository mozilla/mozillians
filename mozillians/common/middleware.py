import re
from contextlib import contextmanager

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.encoding import iri_to_uri

from funfactory.urlresolvers import reverse
from tower import ugettext_lazy as _lazy

from mozillians.common.helpers import redirect


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
