import re
import jinja2
from jingo import register

PARAGRAPH_RE = re.compile(r'(?:\r\n|\r|\n){2,}')


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
