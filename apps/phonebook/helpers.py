import re
import time

import jinja2
from funfactory.urlresolvers import reverse
from funfactory.utils import absolutify
from jingo import register


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

    return dict(image_url=url)


@register.inclusion_tag('phonebook/includes/search_result.html')
@jinja2.contextfunction
def search_result(context, person):
    return dict(person=person)
