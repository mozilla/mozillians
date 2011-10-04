import time

import jinja2
from funfactory.urlresolvers import reverse
from jingo import register


@register.filter
def vouched(user):
    if hasattr(user, 'is_vouched'):
        return user.is_vouched()


@register.inclusion_tag('phonebook/includes/photo.html')
@jinja2.contextfunction
def profile_photo(context, person):
    user = context['request'].user
    me = bool(user.username == person.username)
    url = reverse('phonebook.profile_photo', args=[person.unique_id])

    if me:
        url += '?%d' % int(time.time())

    return dict(image_url=url)
