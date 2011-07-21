"""
LARPER - LDAP Authenticate Resources Per Each Request
"""

import logging
import ldap

from django.conf import settings

log = logging.getLogger('phonebook')

DN_SESSION_KEY = 'larper-dn'

def dn(request, uid):
    """
    An authenticated user's dn is needed for binding
    to an LDAP directory. A user search is performed
    based on the user's uid, which is an email address
    and should be pulled from request.user.username in
    most cases.

    Exceptions:
    Method raises larper.USER_NOT_FOUND if uid is invalid.
    """
    if not DN_SESSION_KEY in request.session:
        _find_and_cache_dn(request, uid)
    return request.session[DN_SESSION_KEY]

class UNKNOWN_USER(Exception):
    """ The LDAP server didn't find a user. """
    pass

def _find_and_cache_dn(request, uid):
    log.debug("Anonymous simple bind to find dn")
    conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI, 2)
    try:
        rs = conn.search_s("ou=people,dc=mozillians,dc=org", ldap.SCOPE_SUBTREE, "(uid=%s)" % uid)
        if len(rs) == 1:                
            dn, u = rs[0]
            request.session[DN_SESSION_KEY] = dn
            log.debug("Cached dn=%s in the session" % dn)
        else:
            raise UNKNOWN_USER("No user with uid '%s' was found." % request.user.username)
    finally:
        conn.unbind()


# HACK, TODO Bug#668308
PASS_SESSION_KEY = 'larper-ct-password'


def password(request):
    """ Not sure if this and store_password belong here..."""
    return request.session[PASS_SESSION_KEY]


def store_password(request, password):
    """
    request - Django web request
    password - A clear text password
    """
    request.session[PASS_SESSION_KEY] = password

