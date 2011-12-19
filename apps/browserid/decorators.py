import urlparse
import ldap

from django.contrib.auth import REDIRECT_FIELD_NAME, logout
from django.contrib.auth.decorators import (login_required as
                                            _login_required)
from django.contrib.auth.views import redirect_to_login

import commonware.log
from statsd import statsd

from larper import UserSession, get_assertion, store_assertion


log = commonware.log.getLogger('m.browserid')


def _redirect(request, login_url, redirect_field_name):
    """Redirects the request based on parameters."""
    path = request.build_absolute_uri()
    # If the login url is the same scheme and net location then just
    # use the path as the "next" url.
    login_scheme, login_netloc = urlparse.urlparse(login_url or
                                                   settings.LOGIN_URL)[:2]
    current_scheme, current_netloc = urlparse.urlparse(path)[:2]
    if ((not login_scheme or login_scheme == current_scheme) and
        (not login_netloc or login_netloc == current_netloc)):
        path = request.get_full_path()
    log.debug('Clearing user session')
    logout(request)
    return redirect_to_login(path, login_url, redirect_field_name)        

def login_required(function=None,
                   redirect_field_name=REDIRECT_FIELD_NAME,
                   login_url='/'):
    """BrowserID sepcific login_required decorator.

    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.

    If the user's session timesout, sasl_interactive_bind
    will fail with a generic error. This is wrapped in a
    ldap.OTHER exception.
    """
    def decorator(view_func):
        def _view(request, *args, **kwargs):
            (asst_hsh, assertion) = get_assertion(request)
            if not asst_hsh or not assertion:
                log.info("No assertion in session")
                return _redirect(request, login_url, redirect_field_name)

            try:
                directory = UserSession(request)
                (registered, unique_id) = directory.registered_user()
            except ldap.OTHER:
                statsd.incr('browserid.session_timedout')
                log.info("Backend session timed out, clearing session assertion")
                return _redirect(request, login_url, redirect_field_name)
            return view_func(request, *args, **kwargs)
        return _view

    if function:
        return decorator(function)
    else:
        return decorator
