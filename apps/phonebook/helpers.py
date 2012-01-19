import re
import time
import hashlib
import urllib

from django.conf import settings

import jinja2
from funfactory.urlresolvers import reverse
from funfactory.utils import absolutify
from jingo import register

from larper import UserSession


PARAGRAPH_RE = re.compile(r'(?:\r\n|\r|\n){2,}')

absolutify = register.function(absolutify)


@register.filter
def paragraphize(value):
    return jinja2.Markup(
            u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', '<br>\n')
                         for p in PARAGRAPH_RE.split(jinja2.escape(value))))


@register.inclusion_tag('phonebook/includes/photo.html')
@jinja2.contextfunction
def profile_photo(context, person):
    user = context['request'].user
    me = bool(user.username == person.username)
    url = reverse('phonebook.profile_photo', args=[person.unique_id])

    if me:
        url += '?%d' % int(time.time())

    needs_master = (user.unique_id == person.unique_id)
    ldap = UserSession.connect(context['request'])
    image = ldap.profile_photo(person.unique_id, use_master=needs_master)

    return dict(image_url=url, gravatar=not image)


@register.inclusion_tag('phonebook/includes/search_result.html')
@jinja2.contextfunction
def search_result(context, person):
    return dict(person=person)


def gravatar(email, default=settings.MEDIA_URL + '/media/img/unknown.png',
             size=175, rating='pg'):
    """Takes an email and returns a gravatar image."""
    return 'http://www.gravatar.com/avatar/%S?%S' % (
            hashlib.md5(email.lower()).hexdigest(),
            urllib.urlencode({'d': default,
                              's': str(size),
                              'r': rating}))
