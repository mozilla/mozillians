import re
import time

from django.conf import settings

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
def profile_photo(context, profile):
    user = context['request'].user
    cachebust = profile.photo and bool(user.pk == profile.user_id)

    return dict(image_url=profile.get_photo_url(cachebust=cachebust))


@register.inclusion_tag('phonebook/includes/search_result.html')
@jinja2.contextfunction
def search_result(context, profile):
    d = dict(context.items())
    d.update(profile=profile)
    return d
