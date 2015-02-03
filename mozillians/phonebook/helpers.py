import re
from datetime import date

from django.conf.locale import LANG_INFO
from django.core.validators import URLValidator
from django.forms import ValidationError
from django.utils.translation import get_language

import jinja2
from jingo import register

from mozillians.users import get_languages_for_locale


PARAGRAPH_RE = re.compile(r'(?:\r\n|\r|\n){2,}')


@register.filter
def paragraphize(value):
    return jinja2.Markup(
            u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', '<br>\n')
                         for p in PARAGRAPH_RE.split(jinja2.escape(value))))


@register.inclusion_tag('includes/search_result.html')
@jinja2.contextfunction
def search_result(context, profile):
    d = dict(context.items())
    d.update(profile=profile)
    return d


@register.function
def get_mozillian_years(userprofile):
    if userprofile.date_mozillian:
        year_difference = date.today().year - userprofile.date_mozillian.year
        return year_difference
    return None


@register.function
def langcode_to_name(code, locale=None):
    """Return the language name for the code in locale.

    If locale is None return in current activated language.
    """

    if not locale:
        locale = get_language()
    translated_languages = get_languages_for_locale(locale)
    try:
        lang = dict(translated_languages)[code]
    except KeyError:
        return code
    return lang


def langname_to_code(name):
    """Return locale code by language name
    Return None for unknown language
    """
    reversed_lang_info = dict((lang['name'].lower(), loc) for loc, lang in LANG_INFO.iteritems())
    return reversed_lang_info.get(name)


@register.filter
def simple_urlize(value):
    """Converts a string to a clickable link. If the string is legitimate
    URL address it returns a clickable link otherwise returns the
    string itself.

    """

    validate_url = URLValidator()

    try:
        validate_url(value)
    except ValidationError:
        return value

    return jinja2.Markup('<a href="%s">%s</a>' % (value, value))
