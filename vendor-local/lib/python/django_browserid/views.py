# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import logging

import six

if six.PY3:
    from urllib import parse as urllib_parse
else:
    import urlparse as urllib_parse


from django.conf import settings
from django.contrib import auth
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import NoReverseMatch
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.views.generic.edit import BaseFormView

from django_browserid.base import BrowserIDException, get_audience, sanity_checks
from django_browserid.forms import BrowserIDForm

# Try to import funfactory's reverse and fall back to django's version.
try:
    from funfactory.urlresolvers import reverse
except ImportError:
    from django.core.urlresolvers import reverse


logger = logging.getLogger(__name__)


class Verify(BaseFormView):
    """
    Login view for django-browserid. Takes in an assertion and sends it to the
    remote verification service to be verified, and logs in the user upon
    success.
    """
    form_class = BrowserIDForm

    @property
    def failure_url(self):
        """
        URL to redirect users to when login fails. This uses the value of
        ``settings.LOGIN_REDIRECT_URL_FAILURE``, and defaults to ``'/'`` if the
        setting doesn't exist.
        """
        return getattr(settings, 'LOGIN_REDIRECT_URL_FAILURE', '/')

    @property
    def success_url(self):
        """
        URL to redirect users to when login succeeds if ``next`` isn't
        specified in the request. This uses the value of
        ``settings.LOGIN_REDIRECT_URL``, and defaults to ``'/'`` if the setting
        doesn't exist.
        """
        return getattr(settings, 'LOGIN_REDIRECT_URL', '/')

    def login_success(self):
        """
        Log the user into the site and redirect them to the post-login URL.

        If ``next`` is found in the request parameters, it's value will be used
        as the URL to redirect to. If ``next`` points to a different host than
        the current request, it is ignored.
        """
        auth.login(self.request, self.user)
        redirect_to = self.request.REQUEST.get('next')

        # Do not accept redirect URLs pointing to a different host.
        if redirect_to:
            netloc = urllib_parse.urlparse(redirect_to).netloc
            if netloc and netloc != self.request.get_host():
                redirect_to = None

        return HttpResponseRedirect(redirect_to or self.get_success_url())

    def login_failure(self, error=None):
        """
        Redirect the user to a login-failed page, and add the
        ``bid_login_failed`` parameter to the URL to signify that login failed
        to the JavaScript.

        :param error:
            If login failed due to an error raised during verification, this
            will be the BrowserIDException instance that was raised.
        """
        failure_url = self.get_failure_url()

        # If this url is a view name, we need to reverse it first to
        # get the url.
        try:
            failure_url = reverse(failure_url)
        except NoReverseMatch:
            pass

        # Append "?bid_login_failed=1" to the URL to notify the
        # JavaScript that the login failed.
        if not failure_url.endswith('?'):
            failure_url += '?' if not '?' in failure_url else '&'

        failure_url += 'bid_login_failed=1'

        return redirect(failure_url)

    def form_valid(self, form):
        """
        Send the given assertion to the remote verification service and,
        depending on the result, trigger login success or failure.

        :param form:
            Instance of BrowserIDForm that was submitted by the user.
        """
        self.assertion = form.cleaned_data['assertion']
        self.audience = get_audience(self.request)

        try:
            self.user = auth.authenticate(
                assertion=self.assertion,
                audience=self.audience
            )
        except BrowserIDException as e:
            return self.login_failure(e)

        if self.user and self.user.is_active:
            return self.login_success()

        return self.login_failure()

    def form_invalid(self, *args, **kwargs):
        """Trigger login failure since the form is invalid."""
        return self.login_failure()

    def get(self, *args, **kwargs):
        """Trigger login failure since we don't support GET on this view."""
        return self.login_failure()

    def get_failure_url(self):
        """
        Retrieve `failure_url` from the class. Raises ImproperlyConfigured if
        the attribute is not found.
        """
        if not self.failure_url:
            raise ImproperlyConfigured('No redirect URL found. Provide a '
                                       '`failure_url`.')
        return self.failure_url

    def dispatch(self, request, *args, **kwargs):
        """Run some sanity checks on the request prior to dispatching it."""
        sanity_checks(request)
        return super(Verify, self).dispatch(request, *args, **kwargs)
