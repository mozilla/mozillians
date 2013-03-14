import hashlib
import re
import urllib

from django.conf import settings
import jinja2
from funfactory.utils import absolutify
from jingo import register

PARAGRAPH_RE = re.compile(r'(?:\r\n|\r|\n){2,}')
DEFAULT_AVATAR = '%simg/unknown.png' % (settings.MEDIA_URL)
absolutify = register.function(absolutify)


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


def gravatar(email, default=DEFAULT_AVATAR, size=175, rating='pg'):
    """Return the Gravatar URL for an email address."""

    return 'http://www.gravatar.com/avatar/%s?%s' % (
            hashlib.md5(email.lower()).hexdigest(),
            urllib.urlencode({'d': absolutify(default),
                              's': str(size),
                              'r': rating}))
