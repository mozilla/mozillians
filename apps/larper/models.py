import ldap
from ldap.dn import explode_dn
from ldap.modlist import modifyModlist
from ldap.filter import filter_format

import logging

from django.conf import settings

import larper
from larper import LDAP_DEBUG

import re

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

        conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI, LDAP_DEBUG)

        try:
            log.debug("Doing bind_s(%s, %s)" % (dn, password, ))
            try:
                o = conn.bind_s(dn, password)
                search_filter = filter_format("(cn=*%s*)", (query, ))
                attrs = None # All for now
                # TODO - optimize ['cn', 'mail']
                # TODO(ozten) use search_ext_s and SimplePagedResultsControl
                try:
                    rs = conn.search_s("ou=people,dc=mozillians,dc=org", ldap.SCOPE_SUBTREE, search_filter, attrs)
                except ldap.SIZELIMIT_EXCEEDED:
                    log.error("Too many results!")
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
        search_filter = filter_format("(uniqueIdentifier=%s)", (query, ))
        attrs = None
        return self._find_by_filter(search_filter, attrs)


    def find_by_dn(self, dn):
        """
        TODO(ozten) Look at allowing LDAP connection to dereference
        these aliases, instead of manually doing the lookup.
        """
        dn_parts = explode_dn(dn)
        query = None
        reg = re.compile('uniqueIdentifier=(.*)', re.IGNORECASE)
        for part in dn_parts:
            matcher = reg.match(part)
            if matcher:
                query = matcher.groups()[0]
                break
        if query:
            return self.find_by_uniqueIdentifier(query)
        else:
            return None


    def _find_by_filter(self, search_filter, attrs):

        person = {}
        uid = self.request.user.username
        dn = larper.dn(self.request, uid)        
        password = larper.password(self.request)

        conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI, LDAP_DEBUG)

        try:
            o = conn.bind_s(dn, password)

            rs = conn.search_s("ou=people,dc=mozillians,dc=org", ldap.SCOPE_SUBTREE, search_filter, attrs)
            if len(rs) > 0:
                if len(rs) > 1:
                    log.warning("Searching for %s gave %d results... expected 0 or 1. Returning the first one.", (search_filter, len(rs)))
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

    def update_person(self, person, profile):
        """
        person - larper.models.Person
        profile - dictionary of attributes
        Somethng old, something new ...
        """
        uid = self.request.user.username
        dn = larper.dn(self.request, uid)        
        password = larper.password(self.request)

        conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI, LDAP_DEBUG)

        try:
            conn.bind_s(dn, password)
            mods = modifyModlist(person, profile, ignore_oldexistent=1)
            conn.modify_s(dn, mods)

        except ldap.INVALID_CREDENTIALS, e:
            log.error(e)
        except ldap.INSUFFICIENT_ACCESS, e:
            log.error(e)
        finally:
            conn.unbind()
