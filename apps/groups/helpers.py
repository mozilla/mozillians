from django.contrib.auth.models import User

import jinja2
from jingo import register

from larper import UserSession


@register.function
def stringify_groups(groups):
    """Change a list of Group objects into a space-delimited string."""
    return u','.join([group.name for group in groups])


@jinja2.contextfunction
def users_from_groups(context, groups, limit=None):
    """Return all Person objects of users in the Group QuerySet.

    This helper exists because of our mixed datastore environment."""
    profiles = groups.userprofile_set.all()
    if limit:
        profiles = profiles[:limit]

    users = User.objects.filter(id__in=[p.user_id for p in profiles])
    ldap = UserSession.connect(context)

    ldap_users = []
    for u in users:
        # We have to walk this so we don't hit LDAP's HARD LIMIT.
        search_result = ldap.search_by_email(u.email)
        if search_result:
            ldap_users.append(search_result[0])

    return ldap_users
