import hashlib
import logging
import urllib

from os import path

from jingo import register

from django.conf import settings
from django.template import Context
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from funfactory.utils import absolutify

logger = logging.getLogger('common.helpers')
absolutify = register.function(absolutify)


def gravatar(email, default=settings.DEFAULT_AVATAR_URL, size=175, rating='pg'):
    """Return the Gravatar URL for an email address."""

    return 'https://secure.gravatar.com/avatar/%s?%s' % (
            hashlib.md5(email.lower()).hexdigest(),
            urllib.urlencode({'d': absolutify(default),
                              's': str(size),
                              'r': rating}))


@register.function
def field_with_attrs(bfield, **kwargs):
    """Allows templates to dynamically add html attributes to bound
    fields from django forms.

    Copied from bedrock.
    """
    if kwargs.get('label', None):
        bfield.label = kwargs['label']
    bfield.field.widget.attrs.update(kwargs)
    return bfield


@register.function
def bootstrap(element):
    """Renders bootstrap forms in jinja2.

    Takes an element that is either a field or an entire form and
    renders the appropriate bootstrap elements.
    """
    element_type = element.__class__.__name__.lower()
    if element_type == 'boundfield':
        template = get_template("bootstrapform/field.html")
        context = Context({'field': element})
    else:
        template = get_template("bootstrapform/form.html")
        context = Context({'form': element})

    return mark_safe(template.render(context))


@register.function
def get_privacy_level(user):
    """Return privacy level user."""
    from apps.users.models import PUBLIC
    if not user.is_authenticated():
        return PUBLIC
    return user.userprofile.level


@register.function
def media(url):
    return path.join(settings.MEDIA_URL, url.lstrip('/'))
