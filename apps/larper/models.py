import ldap

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
        uid = self.request.user.username
        dn = larper.dn(self.request, uid)        
        password = larper.password(self.request)

        conn = ldap.initialize(settings.AUTH_LDAP_SERVER_URI, 2)

        # TODO: cache dn in session too
        try:
            log.debug("Doing bind_s(%s, %s)" % (dn, password, ))
            try:
                o = conn.bind_s(dn, password)
                search_filter = "(cn=*%s*)" % query
                attrs = None # All for now
                # TODO - optimize ['cn', 'mail']
                rs = conn.search_s("ou=people,dc=mozillians,dc=org", ldap.SCOPE_SUBTREE, search_filter, attrs)
                if len(rs) > 0:
                    log.error("Search has results!")
                    for result in rs:
                        dn, person = result
                        log.debug("Results for dn=%s" % dn)
                        log.debug(person)
                else:
                    log.debug('No one with cn=*david* was found')
            except ldap.INVALID_CREDENTIALS, ic:
                log.error(ic)                
        finally:
            conn.unbind()
