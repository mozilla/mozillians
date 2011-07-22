import ldap
from ldap.modlist import modifyModlist
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

    def update_person(self, person, profile):
        """
        person - larper.models.Person
        profile - dictionary of attributes
        Somethng old, something new ...
        """
        uid = self.request.user.username
        dn = larper.dn(self.request, uid)        
        password = larper.password(self.request)

        conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI, 2)

        try:
            conn.bind_s(dn, password)
            log.error("Creating mods from %s" % person)
            
            #modlist = modifyModlist(person, profile, ignore_oldexistent=1)
            mods = self._modlist(profile)
            #log.error("dn = %s modlist = %s" % (dn, mods))
            conn.modify_s(dn, mods)
        except ldap.INVALID_CREDENTIALS, e:
            log.error(e)
        except ldap.INSUFFICIENT_ACCESS, e:
            log.error("TODO(ozten) I'm seeing this, but it should never happen.")
            log.error(e)
        finally:
            conn.unbind()

    def _modlist(self, profile):
        """
        TODO(ozten) We should use modifyModlist, but it
        generates the wrong modlist
        modlist = [(0, 'givenName', 'Hambone'), (1, 'displayName', None), 
        (0, 'displayName', 'Hambone McSlough'), (1, 'cn', None), 
        (0, 'cn', 'Hambone McSlough'), (1, 'sn', None), (0, 'sn', 'McSlough')]
        where 0 is ADD 1 is DELETE and 2 is REPLACE...
        """

        # Required fields
        mods = [(ldap.MOD_REPLACE, 'cn', profile['cn']), 
                (ldap.MOD_REPLACE, 'displayName', profile['displayName']),
                (ldap.MOD_REPLACE, 'sn', profile['sn']),
                (ldap.MOD_REPLACE, 'displayName', profile['displayName']),
                ]

        # Optional fields
        if profile['givenName']:
            mods.append((ldap.MOD_REPLACE, 'givenName', profile['givenName']))
        else:
            mods.append((ldap.MOD_DELETE, 'givenName', None))
        
        return mods
