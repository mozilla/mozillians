import ldap
from ldap.filter import filter_format

import logging

from django.conf import settings

import larper

log = logging.getLogger('phonebook')
log.setLevel(logging.DEBUG)


class Person(object):
    """
    Note: Person is not a Django Model.
    """
    def __init__(self, request):
        self.request = request


    def search(self, query):
        people = []
        uid = self.request.user.username
        dn = larper.dn(self.request, uid)        
        password = larper.password(self.request)

        conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI, 2)

        try:
            log.debug("Doing bind_s(%s, %s)" % (dn, password, ))
            try:
                o = conn.bind_s(dn, password)
                search_filter = filter_format("(cn=*%s*)", (query, ))
                attrs = None # All for now
                # TODO - optimize ['cn', 'mail']
                rs = conn.search_s("ou=people,dc=mozillians,dc=org", ldap.SCOPE_SUBTREE, search_filter, attrs)
                if len(rs) > 0:
                    log.error("Search has results!")
                    for result in rs:
                        dn, person = result
                        people.append(person)
                else:
                    log.debug('No one with cn=*david* was found')
            except ldap.INVALID_CREDENTIALS, ic:
                log.error(ic)                
        finally:
            conn.unbind()
        return people

    def find_by_uniqueIdentifier(self, query):
        """
        Given a uniqueIdentifier, retrieve the one matching
        person or None.

        TODO DRY - extract function
        """
        person = {}
        uid = self.request.user.username
        dn = larper.dn(self.request, uid)        
        password = larper.password(self.request)

        conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI, 2)

        try:
            o = conn.bind_s(dn, password)
            search_filter = filter_format("(uniqueIdentifier=%s)", (query, ))
            attrs = None
            rs = conn.search_s("ou=people,dc=mozillians,dc=org", ldap.SCOPE_SUBTREE, search_filter, attrs)
            if len(rs) > 0:
                if len(rs) > 1:
                    log.warning("Searching for %s gave %d results... expected 0 or 1. Returning the first one.", (query, len(rs)))
                log.error("Search has results!")
                for result in rs:
                    dn, person = result
                    return person
            else:
                log.debug('No one with cn=*david* was found')
        except ldap.INVALID_CREDENTIALS, ic:
            log.error(ic)                
        finally:
            conn.unbind()
