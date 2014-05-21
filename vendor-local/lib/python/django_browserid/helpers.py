# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import json

from django.conf import settings
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from django_browserid.forms import (BROWSERID_SHIM, BrowserIDForm,
                                    FORM_CSS, FORM_JAVASCRIPT)

from django_browserid.util import LazyEncoder, static_url

from six import string_types

# If funfactory is available, we want to use it's locale-aware reverse instead
# of Django's reverse, so we try to import funfactory's first and fallback to
# Django's if it is not found.
try:
    from funfactory.urlresolvers import reverse
except ImportError:
    from django.core.urlresolvers import reverse


def browserid_info(request):
    """
    Output the HTML for the login form and the info tag. Should be called once
    at the top of the page just below the <body> tag.
    """
    form = BrowserIDForm(auto_id=False)

    # Force request_args to be a dictionary, in case it is lazily generated.
    request_args = dict(getattr(settings, 'BROWSERID_REQUEST_ARGS', {}))

    # Only pass an email to the JavaScript if the current user was authed with
    # our auth backend.
    backend = getattr(request.user, 'backend', None)
    if backend == 'django_browserid.auth.BrowserIDBackend':
        email = getattr(request.user, 'email', '')
    else:
        email = ''

    return render_to_string('browserid/info.html', {
        'email': email,
        'login_url': reverse('browserid_login'),
        'request_args': json.dumps(request_args, cls=LazyEncoder),
        'form': form,
    }, RequestContext(request))


def browserid_button(text=None, next=None, link_class=None,
                     attrs=None, href='#'):
    """
    Output the HTML for a BrowserID link.

    :param text:
        Text to use inside the link.

    :param next:
        Value to use for the data-next attribute on the link.

    :param link_class:
        Class to use for the link.

    :param attrs:
        Dictionary of attributes to add to the link. Values here override those
        set by other arguments.

        If given a string, it is parsed as JSON and is expected to be an object.

    :param href:
        href to use for the link.
    """
    attrs = attrs or {}
    if isinstance(attrs, string_types):
        attrs = json.loads(attrs)

    attrs.setdefault('class', link_class)
    attrs.setdefault('href', href)
    attrs.setdefault('data-next', next)
    return render_to_string('browserid/button.html', {
        'text': text,
        'attrs': attrs,
    })


def browserid_login(text='Sign in', color=None, next=None,
                    link_class='browserid-login', attrs=None,
                    fallback_href='#'):
    """
    Output the HTML for a BrowserID login link.

    :param text:
        Text to use inside the link. Defaults to 'Sign in', which is not
        localized.

    :param color:
        Color to use for the login button; this will only work if you have
        included the default CSS provided by
        :py:func:`django_browserid.helpers.browserid_css`.

        Supported colors are: `'dark'`, `'blue'`, and `'orange'`.

    :param next:
        URL to redirect users to after they login from this link. If omitted,
        the LOGIN_REDIRECT_URL setting will be used.

    :param link_class:
        CSS class for the link. `browserid-login` will be added to this
        automatically.

    :param attrs:
        Dictionary of attributes to add to the link. Values here override those
        set by other arguments.

        If given a string, it is parsed as JSON and is expected to be an object.

    :param fallback_href:
        Value to use for the href of the link. If the user has disabled
        JavaScript, the login link will bring them to this page, which can be
        used as a non-JavaScript login fallback.
    """
    if 'browserid-login' not in link_class:
        link_class += ' browserid-login'
    next = next if next is not None else getattr(settings, 'LOGIN_REDIRECT_URL',
                                                 '/')
    if color:
        link_class += ' persona-button {0}'.format(color)
    return browserid_button(text, next, link_class, attrs, fallback_href)


def browserid_logout(text='Sign out', link_class='browserid-logout',
                     attrs=None):
    """
    Output the HTML for a BrowserID logout link.

    :param text:
        Text to use inside the link. Defaults to 'Sign out', which is not
        localized.

    :param link_class:
        CSS class for the link. `browserid-logout` will be added to this
        automatically.

    :param attrs:
        Dictionary of attributes to add to the link. Values here override those
        set by other arguments.

        If given a string, it is parsed as JSON and is expected to be an object.
    """
    if 'browserid-logout' not in link_class:
        link_class += ' browserid-logout'
    return browserid_button(text, None, link_class, attrs,
                            reverse('browserid_logout'))


def browserid_js(include_shim=True):
    """
    Returns <script> tags for the JavaScript required by the BrowserID login
    button. Requires use of the staticfiles app.

    :param include_shim:
        A boolean that determines if the persona.org JavaScript shim is included
        in the output. Useful if you want to minify the button JavaScript using
        a library like django-compressor that can't handle external JavaScript.
    """
    files = [static_url(path) for path in FORM_JAVASCRIPT]
    if include_shim:
        files.append(BROWSERID_SHIM)

    tags = ['<script type="text/javascript" src="{0}"></script>'.format(path)
            for path in files]
    return mark_safe('\n'.join(tags))


def browserid_css():
    """
    Returns <link> tags for the optional CSS included with django-browserid.
    Requires use of the staticfiles app.
    """
    files = [static_url(path) for path in FORM_CSS]

    tags = ['<link rel="stylesheet" href="{0}" />'.format(path)
            for path in files]
    return mark_safe('\n'.join(tags))
