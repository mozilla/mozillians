"""Tests for access control and other rules in LDAP

Most of these focus on ACLs, but some rules are implemented in other ways.
All get tested here as they all contribute to the overall security policy.

Andrew Findlay
21 June 2011
"""

import unittest
import ldap
import ldap.modlist
from ldif import LDIFParser

ldap_url = 'ldap://localhost:1389/'
ldap_suffix = 'dc=mozillians,dc=org'

# Credentials for the all-powerful user
# (Don't put the password for your production server here!)
ldap_rootDN = 'cn=root,dc=mozillians,dc=org'
ldap_rootPW = 'secret'

# The name of the setup file
setup_ldif = 'setup.ldif'

# Keep a list of entries that need deleting in tearDown
global entry_list
entry_list = []

def getAttr( ldap_result, attrname ):
	# ldap_result has the form:
	# (dn, dict)
	# where dict has a list of values for each named attribute
	return ldap_result[1][attrname]

class LdifLoader(LDIFParser):
    def handle(self,dn,entry):
        # print dn
	# Try to delete the entry before adding it, just in case...
	try:
	    self.ldap_handle.delete_s(dn)
	except ldap.NO_SUCH_OBJECT:
	    pass
	# We need to delete this later
	entry_list.append(dn)
	# Add the entry
	self.ldap_handle.add_s(dn,ldap.modlist.addModlist(entry))

class LdapAclTest(unittest.TestCase):

    def setUp(self):
        self.ldap_anon = ldap.initialize(ldap_url)

        self.ldap_rootDN = ldap.initialize(ldap_url)
	self.ldap_rootDN.simple_bind_s(ldap_rootDN,ldap_rootPW)

	ldifparser = LdifLoader(open(setup_ldif, 'r'), None)
	ldifparser.ldap_handle = self.ldap_rootDN
	ldifparser.parse()

    def tearDown(self):
	# print "deleting:"
	# We delete the longest DNs first to avoid trying to delete
	# non-leaf objects
	for dn in sorted(entry_list, key=len, reverse=True):
	    # print dn
	    # It is OK to ignore an error if we are deleting something that
	    # has gone already
	    try:
	        self.ldap_rootDN.delete_s(dn)
            except ldap.NO_SUCH_OBJECT:
	        pass
	    
        self.ldap_anon.unbind()
        self.ldap_rootDN.unbind()


    def test_anon_read_root_DSE_and_schema(self):
	# Read subschemaSubentry from the null DN
        res = self.ldap_anon.search_s(
	        '',
		ldap.SCOPE_BASE,
		filterstr='(objectclass=*)',
		attrlist=['subschemaSubentry'] )
	# We only expect one value here
	schema_ptr = getAttr(res[0],'subschemaSubentry')[0]
	self.assertRegexpMatches(
	        schema_ptr, '^[a-zA-Z]+=',
		'root DSE should contain a valid schema pointer')
	# Now check that we can read the schema
        res = self.ldap_anon.search_s(
	        schema_ptr,
		ldap.SCOPE_BASE,
		filterstr='(objectclass=*)',
		attrlist=['attributetypes','objectclasses'])

    def test_anon_read_suffix(self):
        res = self.ldap_anon.search_s(ldap_suffix,ldap.SCOPE_BASE,'(objectclass=*)')
	self.assertEqual(res[0][0],'dc=mozillians,dc=org', 'suffix entry should have the name dc=mozillians,dc=org')

if __name__ == '__main__':
    unittest.main()

