# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import json
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

import requests


logger = logging.getLogger(__name__)


DEFAULT_HTTP_TIMEOUT = 5
DEFAULT_VERIFICATION_URL = 'https://verifier.login.persona.org/verify'
DEFAULT_PROXY_INFO = None
DEFAULT_DISABLE_CERT_CHECK = False
DEFAULT_HEADERS = {'Content-type': 'application/x-www-form-urlencoded'}


class BrowserIDException(Exception):
    """
    Raised when there is an issue verifying an assertion with
    :func:`django_browserid.base.verify`.
    """
    def __init__(self, exc):
        #: Original exception that caused this to be raised.
        self.exc = exc


def get_audience(request):
    """
    Uses Django settings to format the audience.

    To figure out the audience to use, it does this:

    1. If settings.DEBUG is True and settings.SITE_URL is not set or
       empty, then the domain on the request will be used.

       This is *not* secure!

    2. Otherwise, settings.SITE_URL is checked for the request
       domain and an ImproperlyConfigured error is raised if it
       is not found.

    Examples of settings.SITE_URL::

        SITE_URL = 'http://127.0.0.1:8001'
        SITE_URL = 'https://example.com'
        SITE_URL = 'http://example.com'
        SITE_URL = (
            'http://127.0.0.1:8001',
            'https://example.com',
            'http://example.com'
        )

    """
    req_proto = 'https://' if request.is_secure() else 'http://'
    req_domain = request.get_host()
    req_url = '%s%s' % (req_proto, req_domain)
    site_url = getattr(settings, 'SITE_URL', None)
    if not site_url:
        if settings.DEBUG:
            return req_url
        else:
            raise ImproperlyConfigured('`SITE_URL` must be set. See '
                                       'documentation for django-browserid')
    if isinstance(site_url, basestring):
        site_url = [site_url]
    try:
        url_iterator = iter(site_url)
    except TypeError:
        raise ImproperlyConfigured('`SITE_URL` is not a string or an iterable')
    if req_url not in url_iterator:
        raise ImproperlyConfigured('request `{0}`, was not found in SITE_URL `{1}`'
                                   .format(req_url, site_url))
    return req_url


def _verify_http_request(url, data):
    parameters = {
        'data': data,
        'proxies': getattr(settings, 'BROWSERID_PROXY_INFO',
                           DEFAULT_PROXY_INFO),
        'verify': not getattr(settings, 'BROWSERID_DISABLE_CERT_CHECK',
                              DEFAULT_DISABLE_CERT_CHECK),
        'headers': DEFAULT_HEADERS,
        'timeout': getattr(settings, 'BROWSERID_HTTP_TIMEOUT',
                           DEFAULT_HTTP_TIMEOUT),
    }

    if parameters['verify']:
        parameters['verify'] = getattr(settings, 'BROWSERID_CACERT_FILE', True)

    try:
        r = requests.post(url, **parameters)
    except requests.exceptions.RequestException as e:
        raise BrowserIDException(e)

    try:
        rv = json.loads(r.content)
    except (ValueError, TypeError):
        logger.warning('Failed to decode JSON. Resp: %s, Content: %s',
                       r.status_code, r.content)
        return dict(status='failure')

    return rv


def verify(assertion, audience, extra_params=None, url=None):
    """
    Verify assertion using an external verification service.

    :param assertion:
        The string assertion received in the client from
        ``navigator.id.request()``.
    :param audience:
        This is domain of your website and it must match what
        was in the URL bar when the client asked for an assertion.
        You probably want to use
        :func:`django_browserid.get_audience` which sets it
        based on ``SITE_URL``.
    :param extra_params:
        A dict of additional parameters to send to the
        verification service as part of the POST request.
    :param url:
        A custom verification URL for the service.
        The service URL can also be set using the
        ``BROWSERID_VERIFICATION_URL`` setting.

    :returns:
        A dictionary similar to the following:

        .. code-block:: python

           {
               u'audience': u'https://mysite.com:443',
               u'email': u'myemail@example.com',
               u'issuer': u'browserid.org',
               u'status': u'okay',
               u'expires': 1311377222765
           }

    :raises: BrowserIDException: Error connecting to remote verification
        service.
    """
    if not url:
        url = getattr(settings, 'BROWSERID_VERIFICATION_URL',
                      DEFAULT_VERIFICATION_URL)

    logger.info('Verification URL: %s', url)

    args = {'assertion': assertion, 'audience': audience}
    if extra_params:
        args.update(extra_params)

    result = _verify_http_request(url, args)

    if result['status'] != 'okay':
        logger.warning('BrowserID verification failure. Response: %s '
                       'Audience: %s', result, audience)
        logger.warning('BID assert: %s', assertion)
        return False
    else:
        return result


def sanity_checks(request):
    """Small checks for common errors."""
    if not getattr(settings, 'BROWSERID_DISABLE_SANITY_CHECKS', False):
        return

    # SESSION_COOKIE_SECURE should be False in development unless you can
    # use https.
    if settings.SESSION_COOKIE_SECURE and not request.is_secure():
        logger.warning('SESSION_COOKIE_SECURE is currently set to True, '
                       'which may cause issues with django_browserid '
                       'login during local development. Consider setting '
                       'it to False.')

    # If you're using django-csp, you should include persona.
    if 'csp.middleware.CSPMiddleware' in settings.MIDDLEWARE_CLASSES:
        persona = 'https://login.persona.org'
        in_default = persona in getattr(settings, 'CSP_DEFAULT_SRC', None)
        in_script = persona in getattr(settings, 'CSP_SCRIPT_SRC', None)
        in_frame = persona in getattr(settings, 'CSP_FRAME_SRC', None)

        if (not in_script or not in_frame) and not in_default:
            logger.warning('django-csp detected, but %s was not found in '
                           'your CSP policies. Consider adding it to '
                           'CSP_SCRIPT_SRC and CSP_FRAME_SRC',
                           persona)
