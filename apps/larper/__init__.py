"""
LARPER - LDAP Authenticate Resources Per Each Request
"""

import logging

import ldap
from ldap.modlist import addModlist
from ldap.modlist import modifyModlist

import uuid

from django.conf import settings
from django.core import signing

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


def password(request):
    """ Not sure if this and store_password belong here..."""
    d = request.session.get('PASSWORD')
    if d:
        return signing.loads(d).get('password')


def store_password(request, password):
    """
    request - Django web request
    password - A clear text password
    """
    request.session['PASSWORD'] = signing.dumps({'password': password})


# Increase length of random uniqueIdentifiers as size of Mozillians
# community enters the low millions ;)
UUID_SIZE = 8


def create_person(request, profile, password):
    """
    Given a dictionary of profile attributes, creates
    an LDAP user. Method returns their uid.

    Method raises the following exceptions:
    ...
    """
    conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI, 2)
    try:
        conn.bind_s(settings.LDAP_REGISTRAR_DN,
                    settings.LDAP_REGISTRAR_PASSWORD)
        # TODO catch already exists and keep trying
        # graphite would be great here (create, conflict, etc)
        uniqueIdentifier = str(uuid.uuid4())[0:UUID_SIZE]
        new_dn = "uniqueIdentifier=%s,%s" % (uniqueIdentifier,
                                             settings.LDAP_USERS_GROUP)
        log.debug("new uid=%s so dn=%s" % (uniqueIdentifier, new_dn))

        profile['uniqueIdentifier'] = uniqueIdentifier
        mods = addModlist(profile)
        conn.add_s(new_dn, mods)
        return uniqueIdentifier
    except ldap.INSUFFICIENT_ACCESS, e:
        log.error(e)
        raise
    finally:
        conn.unbind()

def vouch_person(request, voucher, vouchee):
    """
    voucher - A Mozillian
    vouchee - A Pending Account
    A voucher can 'vouch for' another user as 
    being part of the Mozillian community.
    """
    conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI, 2)
    uniqueIdentifier = request.user.ldap_user.attrs['uniqueIdentifier'][0]
    try:
        conn.bind_s(dn(request, uniqueIdentifier), 
                    password(request))
        # TODO get the person and make sure they don't have a mozilliansvouchedBy
        voucher_dn = "uniqueIdentifier=%s,%s" % (voucher,
                                                 settings.LDAP_USERS_GROUP)
        vouchee_dn = "uniqueIdentifier=%s,%s" % (vouchee,
                                                 settings.LDAP_USERS_GROUP)
        modlist = [(ldap.MOD_ADD, 'mozilliansVouchedBy', [voucher_dn])]

        rs = conn.modify_s(vouchee_dn, modlist)
        log.error("We successfully changed our dudez")
        log.error(rs)
        return True
    except ldap.TYPE_OR_VALUE_EXISTS, e:
        log.error("Trying to vouch for an already vouched Mozillian.")
        log.error(e)
        raise
    except ldap.INSUFFICIENT_ACCESS, e:
        log.error(e)
        raise
    finally:
        conn.unbind()
