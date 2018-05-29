import re
from datetime import date

from django.core.validators import URLValidator
from django.forms import ValidationError
from django.utils.translation import get_language

from django_jinja import library
import jinja2

from mozillians.users import get_languages_for_locale
from mozillians.users.models import IdpProfile


PARAGRAPH_RE = re.compile(r'(?:\r\n|\r|\n){2,}')


@library.filter
def paragraphize(value):
    return jinja2.Markup(u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', '<br>\n')
                                      for p in PARAGRAPH_RE.split(jinja2.escape(value))))


@jinja2.contextfunction
@library.global_function
@library.render_with('includes/search_result.html')
def search_result(context, result):
    d = dict(context.items())
    d.update(result=result)
    return d


@library.global_function
def get_mozillian_years(userprofile):
    if userprofile.date_mozillian:
        year_difference = date.today().year - userprofile.date_mozillian.year
        return year_difference
    return None


@library.global_function
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


@library.filter
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


@library.global_function
def get_search_models(models):
    """Generates GET params to specify models."""
    params = ''
    for model in models:
        params += '&models={}'.format(model)
    return params


@library.filter
def get_idp_external_url(obj):
    """Returns a link to the OP based on available options.

    Returns a link to GitHub for obj.type == PROVIDER_GITHUB
    Returns the username as a fallback for other OPs.
    Returns an empty string if there is no username
    """
    if obj.username:
        if obj.type == IdpProfile.PROVIDER_GITHUB:
            username = jinja2.Markup.escape(obj.username)
            github_url = '<a href="https://github.com/{username}" target="_blank">{username}</a>'
            return jinja2.Markup(github_url.format(username=username))
        return obj.username
    return ''
