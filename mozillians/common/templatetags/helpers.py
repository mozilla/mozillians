import urllib
import urlparse

from datetime import datetime, timedelta
from hashlib import md5

from django.conf import settings
from django.contrib.staticfiles.storage import staticfiles_storage
from django.http import HttpResponseRedirect
from django.template.loader import get_template
from django.utils import six
from django.utils.encoding import smart_str
from django.utils.safestring import mark_safe

import bleach
import markdown as markdown_module
from django_jinja import library
from jinja2 import Markup, contextfunction
from pytz import timezone, utc
from sorl.thumbnail import get_thumbnail
from django.utils.translation import ugettext as _

from mozillians.common.urlresolvers import reverse
from mozillians.common import utils

GRAVATAR_URL = 'https://secure.gravatar.com/avatar/{emaildigest}'


@library.global_function
def absolutify(url):
    return utils.absolutify(url)


def _urlencode(items):
    """A Unicode-safe URLencoder."""
    try:
        return urllib.urlencode(items)
    except UnicodeEncodeError:
        return urllib.urlencode([(k, smart_str(v)) for k, v in items])


@library.filter
def urlparams(url_, hash=None, **query):
    """Add a fragment and/or query paramaters to a URL.

    New query params will be appended to exising parameters, except duplicate
    names, which will be replaced.
    """
    url = urlparse.urlparse(url_)
    fragment = hash if hash is not None else url.fragment

    # Use dict(parse_qsl) so we don't get lists of values.
    q = url.query
    query_dict = dict(urlparse.parse_qsl(smart_str(q))) if q else {}
    query_dict.update((k, v) for k, v in query.items())

    query_string = _urlencode([(k, v) for k, v in query_dict.items() if v is not None])
    new = urlparse.ParseResult(url.scheme, url.netloc, url.path, url.params,
                               query_string, fragment)
    return new.geturl()


def gravatar(email, default_avatar_url=settings.DEFAULT_AVATAR_URL, size=175, rating='pg'):
    """Return the Gravatar URL for an email address."""
    url = GRAVATAR_URL.format(emaildigest=md5(email).hexdigest())
    url = urlparams(url, d=utils.absolutify(default_avatar_url), s=size, r=rating)
    return url


@library.global_function
def field_with_attrs(bfield, **kwargs):
    """Allows templates to dynamically add html attributes to bound
    fields from django forms.

    Copied from bedrock.
    """
    if kwargs.get('label', None):
        bfield.label = kwargs['label']
    bfield.field.widget.attrs.update(kwargs)
    return bfield


@library.global_function
def mozillians_field(element, required=False):
    """Renders fields in jinja2.

    Takes a field and renders the appropriate elements.
    """
    template = get_template('includes/field.html')
    context = {'field': element, 'flag_required': required}

    return mark_safe(template.render(context))


@library.global_function
def privacy_field(element):
    element = field_with_attrs(element, **{'class': 'privacy-choice',
                                           'data-privacy-original': element.value(),
                                           'label': _('Visible to:')})
    template = get_template('includes/field.html')
    context = {'field': element, 'privacy': True}
    return mark_safe(template.render(context))


@library.global_function
def mozillians_form(element):
    """Renders forms in jinja2

    Takes a form and renders the appropriate elements.
    """
    template = get_template('includes/form.html')
    context = {'form': element}

    return mark_safe(template.render(context))


@library.global_function
def thumbnail(img, geometry, **kwargs):
    """Proxy to solr's get_thumbnail."""
    return get_thumbnail(img, geometry, **kwargs)


def redirect(to, *args, **kwargs):
    """Redirect with locale support."""
    url = reverse(to, args=args, kwargs=kwargs)
    return HttpResponseRedirect(url)


@library.filter
def markdown(text, allowed_tags=None, allowed_attributes=None, allowed_styles=None):
    if not allowed_tags:
        allowed_tags = ['p', 'em', 'li', 'ul', 'a', 'strong', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    if not allowed_attributes:
        allowed_attributes = ['href']
    if not allowed_styles:
        allowed_styles = []
    text = markdown_module.markdown(text, safe_mode='remove')
    clean_text = bleach.clean(text, allowed_tags, allowed_attributes, allowed_styles, strip=True)
    return Markup(clean_text)


@library.global_function
@contextfunction
def display_context(context, include_callables=False):
    """
    Return a marked-up chunk of content containing the items
    in the template context, if ``settings.DEBUG`` is True.
    Otherwise returns an empty string.

    By default, callables are omitted. Pass include_callables=True
    to include them.

    The format of the result is::

        <dl class="jinja-context">
          <dt>key</dt><dd>value</dd>
          <dt>key</dt><dd>value</dd>
          ...
        </dl>

    ``repr`` is applied to the values to format them.

    Example usage::

        {{ display_context() }}

        {{ display_context(include_callables=True) }}

    """
    if not settings.DEBUG:
        return ''
    keys = sorted(context.keys())
    parts = [
        '<dt>{key}</dt><dd>{value}</dd>'.format(key=key, value=repr(context[key]))
        for key in keys
        if include_callables or not callable(context[key])
    ]
    html = '<dl class="jinja-context">{parts}</dl>'.format(parts=''.join(parts))
    return Markup(html)


@library.global_function
@contextfunction
def get_context(context):
    """
    Provide access to the Jinja :class:`Context` object in case
    you want to do more complicated things with it. Typically,
    ``display_context()`` is easier to use.

    If ``settings.DEBUG`` is not True, returns an empty dictionary.

    Example usage::

        {% set context=get_context() %}
        {% for k, v in context|dictsort %}
            {% if not is_callable(v) %}
                {{ k }}: {{ v }}<br/>
            {% endif %}
        {% endfor %}
    """
    if not settings.DEBUG:
        return {}
    return context


@library.global_function
def is_callable(thing):
    """
    Return True if thing is callable.

    See get_context() for example usage.
    """
    return callable(thing)


@library.filter
def is_checkbox(field):
    return field.field.widget.__class__.__name__.lower() == 'checkboxinput'


@library.filter
def is_radio(field):
    return field.field.widget.__class__.__name__.lower() == 'radioselect'


def aware_utcnow():
    """
    Return timezone-aware now, same way Django does it, but regardless
    of settings.USE_TZ. (This is a separate method so it can be easily
    mocked to test the other methods.)
    """
    return datetime.utcnow().replace(tzinfo=utc)


@library.global_function
def now_in_timezone(timezone_name):
    """
    Return the current time, expressed in the named timezone
    """
    zone = timezone(timezone_name)
    return zone.normalize(aware_utcnow().astimezone(zone))


def offset_of_timezone(timezone_name):
    """
    Return offset from UTC of named time zone, in minutes, as of now.

    This is (time in specified time zone) - (time UTC), so if the time
    zone is 5 hours ahead of UTC, it returns 300.
    """
    now = now_in_timezone(timezone_name)
    offset = now.tzinfo.utcoffset(now)  # timedelta
    minutes = offset.seconds / 60 + offset.days * 24 * 60
    return minutes


def get_datetime(days=0, weeks=0):
    """Return a datetime object, given an offset in days and/or weeks.

    The offset can be either positive or negative.
    """
    return (datetime.today() + timedelta(days=days, weeks=weeks))


def get_object_or_none(model_class, **kwargs):
    """Identical to get_object_or_404, except instead of returning Http404,
    this returns None.

    """
    try:
        return model_class.objects.get(**kwargs)
    except model_class.DoesNotExist:
        return None


@library.global_function
def static(path):
    return staticfiles_storage.url(path)


@library.global_function
def url(viewname, *args, **kwargs):
    """Helper for Django's ``reverse`` in templates."""
    return reverse(viewname, args=args, kwargs=kwargs)


# Port from jingo.helpers

@library.filter
def ifeq(a, b, text):
    """Return ``text`` if ``a == b``."""
    return Markup(text if a == b else '')


@library.filter
def f(s, *args, **kwargs):
    """
    Uses ``str.format`` for string interpolation.
    **Note**: Always converts to s to text type before interpolation.
    >>> {{ "{0} arguments and {x} arguments"|f('positional', x='keyword') }}
    "positional arguments and keyword arguments"
    """
    s = six.text_type(s)
    return s.format(*args, **kwargs)
