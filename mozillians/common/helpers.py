from hashlib import md5

from django.conf import settings
from django.template import Context
from django.template.loader import get_template
from django.utils.safestring import mark_safe

from funfactory.helpers import urlparams
from funfactory import utils
from jingo import register
from sorl.thumbnail import get_thumbnail


GRAVATAR_URL = 'https://secure.gravatar.com/avatar/{emaildigest}'


@register.function
def absolutify(url):
    return utils.absolutify(url)


def gravatar(email, default_avatar_url=settings.DEFAULT_AVATAR_URL,
             size=175, rating='pg'):
    """Return the Gravatar URL for an email address."""
    url = GRAVATAR_URL.format(emaildigest=md5(email).hexdigest())
    url = urlparams(url, d=utils.absolutify(default_avatar_url),
                    s=size, r=rating)
    return url


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
def thumbnail(img, geometry, **kwargs):
    """Proxy to solr's get_thumbnail."""
    return get_thumbnail(img, geometry, **kwargs)
