import hashlib
import re
import urllib

from django.conf import settings
from django.template import Context
from django.template.loader import get_template
from django.utils.safestring import mark_safe

import jinja2
from funfactory.utils import absolutify
from jingo import register
from tower import ugettext_lazy as _lazy

PARAGRAPH_RE = re.compile(r'(?:\r\n|\r|\n){2,}')

absolutify = register.function(absolutify)

# Order sensitive list of permissions. Permissions that get more
# access go higher.

VOUCHED = 20
PUBLIC = 0

PERMISSION_LEVELS = (
    (VOUCHED, _lazy('Vouched')),
    (PUBLIC, _lazy('Public')),
)


@register.filter
def paragraphize(value):
    return jinja2.Markup(
            u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', '<br>\n')
                         for p in PARAGRAPH_RE.split(jinja2.escape(value))))


@register.inclusion_tag('phonebook/includes/search_result.html')
@jinja2.contextfunction
def search_result(context, profile):
    d = dict(context.items())
    d.update(profile=profile)
    return d


def gravatar(
            email,
            default='%simg/unknown.png' % (settings.MEDIA_URL),
            size=175,
            rating='pg'):
    """Return the Gravatar URL for an email address."""

    return 'http://www.gravatar.com/avatar/%s?%s' % (
            hashlib.md5(email.lower()).hexdigest(),
            urllib.urlencode({
                'd': absolutify(default),
                's': str(size),
                'r': rating,
            })
    )


@register.function
def bootstrap(element):
    """
    Renders bootstrap forms in jinja2.

    Takes an element that is either a field or an entire form and renders
    the appropriate bootstrap elements
    """
    element_type = element.__class__.__name__.lower()
    if element_type == 'boundfield':
        template = get_template("bootstrapform/field.html")
        context = Context({'field': element})
    else:
        template = get_template("bootstrapform/form.html")
        context = Context({'form': element})

    return mark_safe(template.render(context))
