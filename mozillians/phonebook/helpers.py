import re
from datetime import date

from django.utils.translation import get_language

import jinja2
from jingo import register

from mozillians.groups.models import GroupMembership
from mozillians.users import get_languages_for_locale

PARAGRAPH_RE = re.compile(r'(?:\r\n|\r|\n){2,}')


@register.filter
def paragraphize(value):
    return jinja2.Markup(
            u'\n\n'.join(u'<p>%s</p>' % p.replace('\n', '<br>\n')
                         for p in PARAGRAPH_RE.split(jinja2.escape(value))))


def search_result_context(context, profile_or_membership):
    """
    Return the template context for search_result.html.
    Has a `profile` and optional `is_pending` and `is_curator` attributes.

    Input might be a UserProfile or a GroupMembership object.
    """
    d = dict(context.items())
    if isinstance(profile_or_membership, GroupMembership):
        membership = profile_or_membership
        profile = membership.userprofile
        profile.is_pending = membership.status == GroupMembership.PENDING
        profile.is_curator = profile == membership.group.curator
    else:
        profile = profile_or_membership
        profile.is_pending = False
        profile.is_curator = False
    d.update(profile=profile)
    return d


@register.inclusion_tag('phonebook/includes/search_result.html')
@jinja2.contextfunction
def search_result(context, profile_or_membership):
    # Actual code broken out to make it testable
    return search_result_context(context, profile_or_membership)


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
