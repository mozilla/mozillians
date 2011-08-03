"""Tests for access control and other rules in LDAP

Most of these focus on ACLs, but some rules are implemented in other ways.
All get tested here as they all contribute to the overall security policy.

The actual tests all have names like test_T1234_mozillian_do_something
where the T1234 bit is a cross-reference to the LDAP design document.
There may be several tests with the same cross-ref.

Andrew Findlay
21 June 2011
"""

import sys
import unittest
import re
import ldap
import ldap.modlist
from ldif import LDIFParser

########################################################################
# Configuration
########################################################################

ldap_url = 'ldap://localhost:1389/'
ldap_suffix = 'dc=mozillians,dc=org'

people_node = 'ou=people,dc=mozillians,dc=org'

# Credentials for the all-powerful user
# (Don't put the password for your production server here!)
ldap_rootDN = 'cn=root,dc=mozillians,dc=org'
ldap_rootPW = 'secret'

# Credentials for an existing non-vouched Applicant
ldap_applicant001DN = 'uniqueIdentifier=test001,ou=people,dc=mozillians,dc=org'
ldap_applicant001PW = 'secret'

# Credentials for an existing vouched Mozillian
ldap_mozillian011DN = 'uniqueIdentifier=test011,ou=people,dc=mozillians,dc=org'
ldap_mozillian011PW = 'secret'
# A sample link entry DN for that user
ldap_link011aDN = 'uniqueIdentifier=a,uniqueIdentifier=test011,ou=people,dc=mozillians,dc=org'

# Credentials for a system account
ldap_sys999DN = 'uid=test999,ou=accounts,ou=system,dc=mozillians,dc=org'
ldap_sys999PW = 'secret'

# DNs of some victims
ldap_applicant002DN = 'uniqueIdentifier=test002,ou=people,dc=mozillians,dc=org'
ldap_mozillian012DN = 'uniqueIdentifier=test012,ou=people,dc=mozillians,dc=org'
ldap_newuserDN = 'uniqueIdentifier=testnew,ou=people,dc=mozillians,dc=org'
ldap_sys900DN = 'uid=test900,ou=accounts,ou=system,dc=mozillians,dc=org'
ldap_mozillian013DN = 'uniqueIdentifier=test013,ou=people,dc=mozillians,dc=org'
ldap_link013DN = 'uniqueIdentifier=1309526546.511499282,uniqueIdentifier=test013,ou=people,dc=mozillians,dc=org'
ldap_table_1DN = 'cn=test-table-1,ou=tables,dc=mozillians,dc=org'
ldap_table_entry_DN = 'textTableKey=irc://irc.mozilla.org/,cn=test-table-1,ou=tables,dc=mozillians,dc=org'
ldap_table_new_entry_DN = 'textTableKey=a,cn=test-table-1,ou=tables,dc=mozillians,dc=org'
test_group = 'cn=test987,ou=groups,ou=system,dc=mozillians,dc=org'


# The root of the system part of the DIT
system_suffix = 'ou=system,dc=mozillians,dc=org'

# Where the LDAP server keeps its monitoring stats
monitor_suffix = 'cn=Monitor'
# ...and the group you have to be in if you want to see that data
monitor_group = 'cn=monitors,ou=groups,ou=system,dc=mozillians,dc=org'

# Group of accounts that may replicate the entire DIT
replicator_group = 'cn=replicators,ou=groups,ou=system,dc=mozillians,dc=org'

# Group of accounts that can manage user and group entries
admin_group = 'cn=LDAPAdmins,ou=groups,ou=system,dc=mozillians,dc=org'

# Group of accounts that can register new users
regAgent_group = 'cn=registrationAgents,ou=groups,ou=system,dc=mozillians,dc=org'

# The name of the setup file
setup_ldif = 'setup.ldif'

########################################################################
# Globals
########################################################################

# Keep a list of entries that need deleting in tearDown
global entry_list
entry_list = []

########################################################################
# Utility functions
########################################################################

# Get list of attributes in result
#
def getAttrNames ( ldap_result ):
    # ldap_result has the form:
    # (dn, dict)
    # where dict has a list of values for each named attribute

    return ldap_result[1].keys()

# Get list of values for attribute
# If there is no such attribute then we return an empty list
#
def getAttrValueList( ldap_result, attrname ):
    # ldap_result has the form:
    # (dn, dict)
    # where dict has a list of values for each named attribute

    # First problem: dictionary keys are case-sensitive.
    #                Attribute names are not.
    myattr = None
    for k in ldap_result[1].keys():
    	if k.lower() == attrname.lower():
	    myattr = k
    return ldap_result[1].get(myattr,[])

# Get the first value of an attribute
# If there is no such attribute then we return None
#
def getAttrValue( ldap_result, attrname ):
    # ldap_result has the form:
    # (dn, dict)
    # where dict has a list of values for each named attribute
    attr_list = getAttrValueList( ldap_result, attrname )
    if not attr_list:
	return None
    else:
	return attr_list[0]

# Check for a value of an attribute that matches a given pattern
#
def attrValueMatch( ldap_result, attrname, pattern ):
    attr_list = getAttrValueList( ldap_result, attrname )
    if not attr_list:
	return None
    else:
        for val in attr_list:
	    # print "TESTING:", val
	    if re.search(pattern,val):
		return True
    return False

# Load an LDIF file
# Used for setting up test cases
#
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


########################################################################
# Common test-fixture code
########################################################################

def setUpCommon(self):
    # Set up the connections, and by doing so implement test_T0005_anon_bind
    try:
	self.ldap_anon = ldap.initialize(ldap_url)

	self.ldap_rootDN = ldap.initialize(ldap_url)
	self.ldap_rootDN.simple_bind_s(ldap_rootDN,ldap_rootPW)

	ldifparser = LdifLoader(open(setup_ldif, 'r'), None)
	ldifparser.ldap_handle = self.ldap_rootDN
	ldifparser.parse()

	self.ldap_applicant001 = ldap.initialize(ldap_url)
	self.ldap_applicant001.simple_bind_s(ldap_applicant001DN,ldap_applicant001PW)

	self.ldap_mozillian011 = ldap.initialize(ldap_url)
	self.ldap_mozillian011.simple_bind_s(ldap_mozillian011DN,ldap_mozillian011PW)

	self.ldap_sys999 = ldap.initialize(ldap_url)
	self.ldap_sys999.simple_bind_s(ldap_sys999DN,ldap_sys999PW)

    except ldap.LDAPError:
		self.fail( "LDAP connection setup error " + str(sys.exc_info()[0]) )


def tearDownCommon(self):
    global entry_list

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
	
    # We have deleted everything that was on the list
    entry_list = []

    self.ldap_anon.unbind()
    self.ldap_rootDN.unbind()
    self.ldap_applicant001.unbind()
    self.ldap_mozillian011.unbind()
    self.ldap_sys999.unbind()


# Changing password
def change_and_check_password(self, user, userDN, ldap_conn, old_pw, new_pw):
    try:
	ldap_conn.passwd_s(userDN, old_pw, new_pw)
    except:
	self.fail( user + " cannot change password: " + str(sys.exc_info()[0]) )

    try:
	ldap_check = ldap.initialize(ldap_url)
	ldap_check.simple_bind_s(userDN, new_pw)
    except:
	self.fail( user + " cannot bind with new password: " + str(sys.exc_info()[0]) )

    ldap_check.unbind()

########################################################################
# Tests
########################################################################

class LdapUserTests(unittest.TestCase):

    def setUp(self):
    	setUpCommon(self)

    def tearDown(self):
    	tearDownCommon(self)

    # All users including Anon should be able to read the schema
    def read_root_DSE_and_schema(self, user, ldap_conn):
	# Read subschemaSubentry from the null DN
	try:
	    res = ldap_conn.search_s(
		    '',
		    ldap.SCOPE_BASE,
		    filterstr='(objectclass=*)',
		    attrlist=['subschemaSubentry'] )

	    # We only expect one value here
	    schema_ptr = getAttrValue(res[0],'subschemaSubentry')
	    if schema_ptr:
		self.assertTrue(re.match('^[a-zA-Z]+=', schema_ptr),
			'root DSE should contain a valid schema pointer')
            else:
	        self.fail( user + " did not get a subschemaSubentry attribute from the root DSE" )

        except ldap.LDAPError:
	    self.fail( user + " cannot read root DSE " + str(sys.exc_info()[0]) )

	# Now check that we can read the schema
	try:
	    res = ldap_conn.search_s(
		    schema_ptr,
		    ldap.SCOPE_BASE,
		    filterstr='(objectclass=*)',
		    attrlist=['attributetypes','objectclasses'])
        except ldap.LDAPError:
	    self.fail( user + " cannot read schema subentry " + schema_ptr + " " + str(sys.exc_info()[0]) )

        # Did we get any Mozillians attributes?
	self.assertTrue( attrValueMatch( res[0], 'attributetypes', 'mozillians' ),
	                 "Mozillians attribute types must be listed in schema" )


    # Changing own user attributes
    def change_user_attributes(self, user, userDN, ldap_conn):
        try:
	    ldap_conn.modify_s(
	        userDN,
		    [
		        (ldap.MOD_REPLACE,'cn','modified CN'),
		        (ldap.MOD_REPLACE,'givenName','modified givenName'),
		        (ldap.MOD_REPLACE,'sn','modified SN'),
		        (ldap.MOD_REPLACE,'displayName','modified displayName'),
		        (ldap.MOD_REPLACE,'mail',['new@mail.one','new@mail.two']),
		        (ldap.MOD_REPLACE,'uid','modified UID'),
		        (ldap.MOD_REPLACE,'telephoneNumber',['+1 234','+5-678-90']),
		        (ldap.MOD_REPLACE,'description','modified description'),
		        (ldap.MOD_REPLACE,'jpegPhoto','modified jpegPhoto'),
		    ]
		)
        except ldap.LDAPError:
	    self.fail( user + " cannot modify their own user atttributes " + str(sys.exc_info()[0]) )



    #######################################################################################
    # Actual tests start here
    #######################################################################################

    def test_T0015_anon_read_suffix(self):
        res = self.ldap_anon.search_s(ldap_suffix,ldap.SCOPE_BASE,'(objectclass=*)')
	self.assertTrue( attrValueMatch( res[0], 'dc', 'mozillians' ),
	         'suffix entry should have an attribute dc=mozillians')

    def test_T0016_anon_read_people_container(self):
        res = self.ldap_anon.search_s(people_node,ldap.SCOPE_BASE,'(objectclass=*)')
	self.assertTrue( attrValueMatch( res[0], 'ou', 'people' ),
	         'ou=people entry should have an attribute ou=people')

    def test_T0010_anon_read_root_DSE_and_schema(self):
	self.read_root_DSE_and_schema("Anon", self.ldap_anon)

    def test_T0010_applicant_read_root_DSE_and_schema(self):
	self.read_root_DSE_and_schema("Applicant 001", self.ldap_applicant001)

    def test_T0010_mozillian_read_root_DSE_and_schema(self):
	self.read_root_DSE_and_schema("Mozillian 011", self.ldap_mozillian011)

    def test_T0020_anon_search_person(self):
	# Anon trying to find a person entry
	# This should work, but not expose any data apart from the DN
	try:
	    res = self.ldap_anon.search_s(
		    people_node,
		    ldap.SCOPE_SUBTREE,
		    filterstr='(uid=test002)' )

	    self.assertEqual( len(res), 1,
	            "Anon search for (uid=test002) should return exactly one entry. We got "+str(len(res)) )
            # print res[0]
        except ldap.LDAPError:
	    self.fail( "Anon cannot search under "+people_node+" " + str(sys.exc_info()[0]) )

        # Now test to see if we got any attributes that we should not see
	for attr in getAttrNames(res[0]):
	    if attr.lower() != 'uniqueIdentifier'.lower():
	        self.fail( "Anon should not be able to read attributes from user entries. Got: " +
		           str(getAttrNames(res[0])) )

    def test_T0030_anon_search_multi(self):
	# Anon trying to find multiple entries
	# This should limit at 2 entries returned but the search filter matches 3
	# so we expect to get an exception.
	# LDAP actually supplies the entries, but Python LDAP does not deliver them to us.
	try:
	    self.assertRaises(ldap.SIZELIMIT_EXCEEDED, lambda:\
                                  self.ldap_anon.search_s(people_node, ldap.SCOPE_SUBTREE, filterstr='(uid=test00*)'))

        except ldap.LDAPError:
	    self.fail( "Anon cannot search under "+people_node+" " + str(sys.exc_info()[0]) )

    def test_T0040_anon_fake_vouch_for_applicant(self):
	# Anon should not be able to put a DN into
	# an applicant's mozilliansVouchedBy attribute
        modlist = [ (ldap.MOD_ADD,'mozilliansVouchedBy',ldap_applicant001DN) ]
        self.assertRaises(ldap.LDAPError, lambda:\
                              self.ldap_anon.modify_s(ldap_applicant001DN, modlist))
                           

    def test_T0040_anon_fake_cn(self):
	# Anon should not be able to put a value into
	# an applicant's cn attribute
        modlist = [ (ldap.MOD_REPLACE,'cn','modified CN') ]
        self.assertRaises(ldap.LDAPError, lambda:\
                          self.ldap_anon.modify_s(ldap_applicant001DN, modlist))
                           

    def test_T9024_anon_read_table(self):
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
	    self.ldap_anon.search_s(
		    ldap_table_1DN,
		    ldap.SCOPE_SUBTREE,
		    filterstr='(textTableKey=*)'
		))

    def test_T9024_anon_read_table_entry(self):
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
	    self.ldap_anon.search_s(
		    ldap_table_entry_DN,
		    ldap.SCOPE_SUBTREE,
		    filterstr='(textTableKey=*)'
		))

    def test_T6040_applicant_search_person(self):
	# Applicant trying to find a person entry that is not their own
	# This should work, but not expose any data apart from the DN
	try:
	    res = self.ldap_applicant001.search_s(
		    people_node,
		    ldap.SCOPE_SUBTREE,
		    filterstr='(uid=test002)' )

	    self.assertEqual( len(res), 1,
	            "Applicant search for (uid=test002) should return exactly one entry. We got "+str(len(res)) )
        except ldap.LDAPError:
	    self.fail( "Applicant cannot search under "+people_node+" " + str(sys.exc_info()[0]) )

        # Now test to see if we got any attributes that we should not see
	for attr in getAttrNames(res[0]):
	    if attr.lower() != 'uniqueIdentifier'.lower():
	        self.fail( "Applicant should not be able to read attributes from user entries. Got: " +
		           str(getAttrNames(res[0])) )

    def test_T6040_applicant_search_links(self):
	# Applicant should not get an error when trying this,
	# but they should not get any results either
	res = self.ldap_applicant001.search_s(
		ldap_mozillian013DN,
		ldap.SCOPE_SUBTREE,
		filterstr='(mozilliansServiceURI=*)' )
	self.assertEqual( len(res), 0,
		"Applicant search for links should return zero entries. We got "+str(len(res)) )

    def test_T9020_applicant_read_table(self):
        try:
	    res = self.ldap_applicant001.search_s(
		    ldap_table_1DN,
		    ldap.SCOPE_SUBTREE,
		    filterstr='(textTableKey=*)'
		)
        except ldap.LDAPError:
	    self.fail( "Applicant cannot search under "+ldap_table_1DN+" " + str(sys.exc_info()[0]) )
	self.assertTrue( len(res) > 0,
		"Applicant search of table should return at least one entry. We got "+str(len(res)) )


# It is not practical to enforce different limits on Applicants and Mozillians
# with the current implementation because the limits statement in OpenLDAP does not accept
# set specifications
#
#    def test_T6050_applicant_search_multi(self):
#	# Applicant trying to find multiple entries
#	# The filter matches 3 in this case
#	# This should limit at 2 entries returned
#	try:
#	    self.assertRaises(ldap.SIZELIMIT_EXCEEDED,
#		self.ldap_applicant001.search_s, 
#			(people_node,
#			ldap.SCOPE_SUBTREE,
#			filterstr='(uid=test00*)' ) )
#
#        except ldap.LDAPError:
#	    self.fail( "Applicant cannot search under "+people_node+" " + str(sys.exc_info()[0]) )

    def test_T6030_mozillian_search_mozillian(self):
	# Mozillian searching for a person entry (another Mozillian in this case)
	try:
	    res = self.ldap_mozillian011.search_s(
		    people_node,
		    ldap.SCOPE_SUBTREE,
		    filterstr='(uid=test012)' )

	    self.assertEqual( len(res), 1,
	            "Mozillian search for (uid=test012) should return exactly one entry. We got "+str(len(res)) )
            # print res[0]
        except ldap.LDAPError:
	    self.fail( "Mozillian cannot search under "+people_node+" " + str(sys.exc_info()[0]) )

	# Check that we got values for the basic attributes
	if not getAttrValue(res[0],'objectClass'):
	    self.fail( "Mozillian should see the objectClass value" )
	if not getAttrValue(res[0],'cn'):
	    self.fail( "Mozillian should see the cn value" )
	if not getAttrValue(res[0],'givenName'):
	    self.fail( "Mozillian should see the givenName value" )
	if not getAttrValue(res[0],'sn'):
	    self.fail( "Mozillian should see the sn value" )
	if not getAttrValue(res[0],'uid'):
	    self.fail( "Mozillian should see the uid value" )
	if not getAttrValue(res[0],'uniqueIdentifier'):
	    self.fail( "Mozillian should see the uniqueIdentifier value" )
	if not getAttrValue(res[0],'mozilliansVouchedBy'):
	    self.fail( "Mozillian should see the mozilliansVouchedBy value" )

        # Now test to see if we got any attributes that we should not see (T1050)
	if getAttrValue(res[0],'userPassword'):
	    self.fail( "Mozillian should not be able to read passwords" )


    def test_T6085_mozillian_search_links(self):
	# Mozillian searching for a link entry
	try:
	    res = self.ldap_mozillian011.search_s(
		    ldap_mozillian013DN,
		    ldap.SCOPE_SUBTREE,
		    filterstr='(mozilliansServiceURI=*)' )
        except ldap.LDAPError:
	    self.fail( "Mozillian cannot search for link entries under "+ldap_mozillian013DN+" " + str(sys.exc_info()[0]) )

	# Check that we got values for the basic attributes
	if not getAttrValue(res[0],'objectClass'):
	    self.fail( "Mozillian should see the objectClass value in a link entry" )
	if not getAttrValue(res[0],'mozilliansServiceURI'):
	    self.fail( "Mozillian should see the mozilliansServiceURI value in a link entry" )
	if not getAttrValue(res[0],'mozilliansServiceID'):
	    self.fail( "Mozillian should see the mozilliansServiceID value in a link entry" )


    def test_T6030_mozillian_search_applicant(self):
	# Mozillian searching for a person entry (an applicant in this case)
	try:
	    res = self.ldap_mozillian011.search_s(
		    people_node,
		    ldap.SCOPE_SUBTREE,
		    filterstr='(uid=test002)' )

	    self.assertEqual( len(res), 1,
	            "Mozillian search for (uid=test002) should return exactly one entry. We got "+str(len(res)) )
            # print res[0]
        except ldap.LDAPError:
	    self.fail( "Mozillian cannot search under "+people_node+" " + str(sys.exc_info()[0]) )

	# Check that we got values for the basic attributes
	if not getAttrValue(res[0],'objectClass'):
	    self.fail( "Mozillian should see the objectClass value" )
	if not getAttrValue(res[0],'cn'):
	    self.fail( "Mozillian should see the cn value" )
	if not getAttrValue(res[0],'givenName'):
	    self.fail( "Mozillian should see the givenName value" )
	if not getAttrValue(res[0],'sn'):
	    self.fail( "Mozillian should see the sn value" )
	if not getAttrValue(res[0],'uid'):
	    self.fail( "Mozillian should see the uid value" )
	if not getAttrValue(res[0],'uniqueIdentifier'):
	    self.fail( "Mozillian should see the uniqueIdentifier value" )

        # Now test to see if we got any attributes that we should not see (T1050)
	if getAttrValue(res[0],'userPassword'):
	    self.fail( "Mozillian should not be able to read passwords" )

	# There should not be a vouched entry in an applicant
	if getAttrValue(res[0],'mozilliansVouchedBy'):
	    self.fail( "Mozillian should see the mozilliansVouchedBy value" )

    def test_T6060_mozillian_delete_applicant(self):
        self.assertRaises(ldap.LDAPError,
                          self.ldap_mozillian011.delete_s,
                          (ldap_applicant002DN))

    def test_T6060_mozillian_delete_self(self):
        self.assertRaises(ldap.LDAPError,
                          self.ldap_mozillian011.delete_s,
                          (ldap_mozillian011DN))


    def test_T0030_mozillian_search_multi(self):
	# Mozillian trying to find multiple entries
	# This should limit at rather more than 2 entries returned
	try:
	    res = self.ldap_mozillian011.search_s(
		    people_node,
		    ldap.SCOPE_SUBTREE,
		    filterstr='(uid=test*)' )

	    self.assertTrue( len(res) > 2,
	            "Mozillian search for (uid=test*) should return more than 2 entries. We got "+str(len(res)) )
            # print res[0]
        except ldap.LDAPError:
	    self.fail( "Mozillian cannot search under "+people_node+" " + str(sys.exc_info()[0]) )


    def test_T9020_mozillian_read_table(self):
        try:
	    res = self.ldap_mozillian011.search_s(
		    ldap_table_1DN,
		    ldap.SCOPE_SUBTREE,
		    filterstr='(textTableKey=*)'
		)
        except ldap.LDAPError:
	    self.fail( "Mozillian cannot search under "+ldap_table_1DN+" " + str(sys.exc_info()[0]) )
	self.assertTrue( len(res) > 0,
		"Mozillian search of table should return at least one entry. We got "+str(len(res)) )

    def test_T9025_mozillian_fake_table_data(self):
	# Mozillian should not be able to modify any table entry
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
	    self.ldap_mozillian011.modify_s(
		    ldap_table_entry_DN,
		    [ (ldap.MOD_REPLACE,'textTableValue','Fake!') ]
		))

    def test_T1010_applicant_change_password(self):
        change_and_check_password(
		self,
	        'Applicant',
                ldap_applicant001DN,
		self.ldap_applicant001,
		None,
		'evenmoresecret' )

    def test_T1010_mozillian_change_password(self):
        change_and_check_password(
		self,
	        'Mozillian',
                ldap_mozillian011DN,
		self.ldap_mozillian011,
		None,
		'evenmoresecret' )

    def test_T1020_change_others_password(self):
	# Try to change other people's passwords
	self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_mozillian011.passwd_s(ldap_applicant002DN, None, 'owned!'))

	self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_mozillian011.passwd_s(ldap_mozillian012DN, None, 'owned!'))

	self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_applicant001.passwd_s(ldap_applicant002DN, None, 'owned!'))

	self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_applicant001.passwd_s(ldap_mozillian012DN, None, 'owned!'))

    def test_T6010_applicant_change_user_attributes(self):
        self.change_user_attributes(
	        'Applicant',
                ldap_applicant001DN,
		self.ldap_applicant001 )

    def test_T6010_mozillian_change_user_attributes(self):
        self.change_user_attributes(
	        'Mozillian',
                ldap_mozillian011DN,
		self.ldap_mozillian011 )

    def test_T6010_mozillian_delete_uid(self):
	# Users should not be able to delete uid as then it will be
	# impossible for them to log in again
	# The error here is OBJECT_CLASS_VIOLATION because this is enforced
	# by a DIT content rule rather than an ACL
        modlist = [ (ldap.MOD_DELETE,'uid',None), ] 
        self.assertRaises(ldap.OBJECT_CLASS_VIOLATION, lambda:\
                          self.ldap_mozillian011.modify_s(ldap_mozillian011DN, modlist))


    def test_T6020_mozillian_read_obscure_attrs(self):
	# Mozillian reading more obscure attributes in their own entry
	try:
	    res = self.ldap_mozillian011.search_s(
		    ldap_mozillian011DN,
		    ldap.SCOPE_BASE,
		    filterstr='(objectclass=*)',
		    attrlist=['mozilliansVouchedBy','modifiersName','modifyTimestamp','userPassword'] )
        except ldap.LDAPError:
	    self.fail( "Mozillian cannot search own entry " + str(sys.exc_info()[0]) )

	if not getAttrValue(res[0],'modifiersName'):
	    self.fail( "Mozillian should see their own modifiersName value" )
	if not getAttrValue(res[0],'modifyTimestamp'):
	    self.fail( "Mozillian should see their own modifyTimestamp value" )
	if not getAttrValue(res[0],'mozilliansVouchedBy'):
	    self.fail( "Mozillian should see their own mozilliansVouchedBy value" )
	# Should NOT see own password (T1050)
	if getAttrValue(res[0],'userPassword'):
	    self.fail( "Mozillian should not see their own userPassword value" )

    def test_T6020_applicant_read_own_attrs(self):
	# Applicant reading common attributes in their own entry
	try:
	    res = self.ldap_applicant001.search_s(
		    ldap_applicant001DN,
		    ldap.SCOPE_BASE,
		    filterstr='(objectclass=*)' )
        except ldap.LDAPError:
	    self.fail( "Applicant cannot search own entry " + str(sys.exc_info()[0]) )

	if not getAttrValue(res[0],'objectClass'):
	    self.fail( "Applicant should see their own objectClass value" )
	if not getAttrValue(res[0],'cn'):
	    self.fail( "Applicant should see their own cn value" )
	if not getAttrValue(res[0],'givenName'):
	    self.fail( "Mozillian should see the givenName value" )
	if not getAttrValue(res[0],'sn'):
	    self.fail( "Applicant should see their own sn value" )
	if not getAttrValue(res[0],'description'):
	    self.fail( "Applicant should see their own description value" )
	if not getAttrValue(res[0],'mail'):
	    self.fail( "Applicant should see their own mail value" )

    def test_T6020_applicant_read_obscure_attrs(self):
	# Applicant reading more obscure attributes in their own entry
	try:
	    res = self.ldap_applicant001.search_s(
		    ldap_applicant001DN,
		    ldap.SCOPE_BASE,
		    filterstr='(objectclass=*)',
		    attrlist=['mozilliansVouchedBy','modifiersName','modifyTimestamp','userPassword'] )
        except ldap.LDAPError:
	    self.fail( "Applicant cannot search own entry " + str(sys.exc_info()[0]) )

	if not getAttrValue(res[0],'modifiersName'):
	    self.fail( "Applicant should see their own modifiersName value" )
	if not getAttrValue(res[0],'modifyTimestamp'):
	    self.fail( "Applicant should see their own modifyTimestamp value" )
	# There should not be a mozilliansVouchedBy value in an applicant entry!
	if getAttrValue(res[0],'mozilliansVouchedBy'):
	    self.fail( "Applicant should not have a mozilliansVouchedBy value" )
	# Should NOT see own password (T1050)
	if getAttrValue(res[0],'userPassword'):
	    self.fail( "Applicant should not see their own userPassword value" )


    def test_T5010_mozillian_vouch_for_applicant(self):
        try:
	    self.ldap_mozillian011.modify_s(
		    ldap_applicant001DN,
		    [ (ldap.MOD_ADD,'mozilliansVouchedBy',ldap_mozillian011DN) ]
		)
        except ldap.LDAPError:
	    self.fail( "Mozillian cannot vouch for applicant " + str(sys.exc_info()[0]) )

    def test_T5010_mozillian_fake_vouch_for_applicant(self):
	# Mozillian should not be able to put someone else's DN into
	# an applicant's mozilliansVouchedBy attribute
        modlist = [ (ldap.MOD_ADD,'mozilliansVouchedBy',ldap_applicant001DN) ]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_mozillian011.modify_s(ldap_applicant001DN, modlist))
                           

    def test_T5010_mozillian_unvouch_applicant(self):
	# Mozillian should not be able to remove any value from
	# an applicant's mozilliansVouchedBy attribute
        modlist = [ (ldap.MOD_DELETE,'mozilliansVouchedBy',None) ]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
	                  self.ldap_mozillian011.modify_s(ldap_applicant001DN, modlist))
                           

    def test_T5020_mozillian_fake_vouch_for_self(self):
	# Mozillian should not be able to modify
	# their own mozilliansVouchedBy attribute
        modlist = [ (ldap.MOD_ADD,'mozilliansVouchedBy',ldap_applicant001DN) ]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_mozillian011.modify_s(ldap_mozillian011DN, modlist))
                           

    def test_T5020_applicant_fake_vouch_for_self(self):
	# Applicant should not be able to modify
	# their own mozilliansVouchedBy attribute
        modlist = [ (ldap.MOD_ADD,'mozilliansVouchedBy',ldap_applicant001DN) ]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_applicant001.modify_s(ldap_applicant001DN, modlist))


    def test_T5020_mozillian_fake_unvouch_self(self):
	# Mozillian should not be able to modify
	# their own mozilliansVouchedBy attribute
        modlist = [ (ldap.MOD_DELETE,'mozilliansVouchedBy',None) ]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                              self.ldap_mozillian011.modify_s(ldap_mozillian011DN, modlist))
                           

    def test_T5030_applicant_fake_vouch_for_another(self):
	# Applicant should not be able to modify
	# another applicant's mozilliansVouchedBy attribute
        modlist = [ (ldap.MOD_ADD,'mozilliansVouchedBy',ldap_applicant001DN) ]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_applicant001.modify_s(ldap_applicant002DN, modlist))
                           

    def test_T6080_mozillian_manage_links(self):
	try:
	    self.ldap_mozillian011.add_s(
		    ldap_link011aDN,
		    [
			('objectClass', 'mozilliansLink'),
			('uniqueIdentifier', 'a'),
			('mozilliansServiceURI', 'irc://irc.mozilla.org/'),
			('mozilliansServiceID', 'testeleven')
		    ]
		)
	    # Make sure that we clear this entry up afterwards
	    entry_list.append(ldap_link011aDN)
        except ldap.LDAPError:
	    self.fail( "Mozillian cannot add link entry "+ldap_link011aDN+" " + str(sys.exc_info()[0]) )

        try:
	    self.ldap_mozillian011.modify_s(
		    ldap_link011aDN,
		    [
			(ldap.MOD_REPLACE,'mozilliansServiceID','test-11')
		    ]
		)
        except ldap.LDAPError:
	    self.fail( "Mozillian cannot modify link entry "+ldap_link011aDN+" " + str(sys.exc_info()[0]) )

        try:
	    self.ldap_mozillian011.delete_s(ldap_link011aDN)
        except ldap.LDAPError:
	    self.fail( "Mozillian cannot delete own link entry "+ldap_link011aDN+" " + str(sys.exc_info()[0]) )


    def test_T6086_mozillian_hack_links(self):
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
	    self.ldap_mozillian011.modify_s(
		    ldap_link013DN,
		    [
			(ldap.MOD_REPLACE,'mozilliansServiceID','owned!')
		    ]
		))


    def test_T7030_mozillian_add_entry(self):
	# Should not be able to add entries
	global entry_list
        modlist = [('objectClass', ['inetOrgPerson','mozilliansPerson']),
                   ('uniqueIdentifier', 'testnew'),
                   ('uid', 'testnew'),
                   ('cn', 'Test new user'),
                   ('givenName', 'Tess'),
                   ('sn', 'Test')]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                              self.ldap_mozillian011.add_s(ldap_newuserDN, modlist))

	# Make sure that we clear this entry up afterwards
        entry_list.append(ldap_newuserDN)

    def test_T7030_applicant_add_entry(self):
	# Should not be able to add entries
	global entry_list
        modlist = [('objectClass', ['inetOrgPerson','mozilliansPerson']),
                   ('uniqueIdentifier', 'testnew'),
                   ('uid', 'testnew'),
                   ('cn', 'Test new user'),
                   ('givenName', 'Tess'),
                   ('sn', 'Test')]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_applicant001.add_s(ldap_newuserDN, modlist))
                           
	# Make sure that we clear this entry up afterwards
        entry_list.append(ldap_newuserDN)

    def test_T8010_mozillian_hack_people_node(self):
        modlist = [(ldap.MOD_REPLACE,'description','Bad, very bad...'),]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_mozillian011.modify_s(people_node, modlist))
        

    def test_T8010_applicant_hack_people_node(self):
        modlist = [(ldap.MOD_REPLACE,'description','Bad, very bad...'),]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_applicant001.modify_s(people_node, modlist))

    def test_T8030_applicant_snooping_on_system_tree(self):
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                              self.ldap_applicant001.search_s(system_suffix,ldap.SCOPE_BASE,'(objectclass=*)'))

        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                              self.ldap_applicant001.search_s(system_suffix,ldap.SCOPE_SUBTREE,'(objectclass=*)'))
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                              self.ldap_applicant001.search_s(admin_group,ldap.SCOPE_BASE,'(objectclass=*)'))

    def test_T8030_mozillian_snooping_on_system_tree(self):
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                          self.ldap_mozillian011.search_s(system_suffix,ldap.SCOPE_BASE,'(objectclass=*)'))
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                          self.ldap_mozillian011.search_s(system_suffix,ldap.SCOPE_SUBTREE,'(objectclass=*)'))
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                          self.ldap_mozillian011.search_s(admin_group,ldap.SCOPE_BASE,'(objectclass=*)'))


    def test_T9010_uid_must_be_unique(self):
	# There is already an entry with uid=test002 in the test data
	# so we should not be able to change our own UID to clash
        modlist = [ (ldap.MOD_REPLACE,'uid','test002'), ]
        self.assertRaises(ldap.CONSTRAINT_VIOLATION, lambda:\
                          self.ldap_mozillian011.modify_s(ldap_mozillian011DN, modlist))
        

    def test_T9010_uid_must_be_unique_even_when_forced(self):
	# There is already an entry with uid=test002 in the test data
	# so even rootDN should not be able to change a UID to clash
        modlist = [(ldap.MOD_REPLACE,'uid','test002'), ]
        self.assertRaises(ldap.CONSTRAINT_VIOLATION, lambda:\
                          self.ldap_rootDN.modify_s(ldap_mozillian011DN, modlist))



class LdapMonitorUserTests(unittest.TestCase):

    # These tests require a system user in the Monitor group
    #
    # Note also that most of the attributes we want are 'operational'
    # so we must request them by name
    # (or use the '*' '+' convention: OpenLDAP supports that, but some others don't)

    def setUp(self):
    	setUpCommon(self)
	# Add test user to group
	self.ldap_rootDN.modify_s(
		monitor_group,
		[ (ldap.MOD_ADD,'member',ldap_sys999DN) ]
	    )

    def tearDown(self):
	# Remove test user from group
	self.ldap_rootDN.modify_s(
		monitor_group,
		[ (ldap.MOD_DELETE,'member',ldap_sys999DN) ]
	    )
	# Now clear out test entries and close connections
    	tearDownCommon(self)

    def test_T7050_mozillian_snooping_on_stats(self):
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                          self.ldap_mozillian011.search_s(monitor_suffix,ldap.SCOPE_BASE,'(objectclass=*)'))
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                          self.ldap_mozillian011.search_s(monitor_suffix,ldap.SCOPE_SUBTREE,'(objectclass=*)'))

    def test_T7050_anon_snooping_on_stats(self):
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                              self.ldap_anon.search_s(monitor_suffix,ldap.SCOPE_BASE,'(objectclass=*)'))
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                              self.ldap_anon.search_s(monitor_suffix,ldap.SCOPE_SUBTREE,'(objectclass=*)'))

    def test_T7050_monitor_read_suffix(self):
        try:
	    res = self.ldap_sys999.search_s(
	            monitor_suffix,
		    ldap.SCOPE_BASE,
		    filterstr='(objectclass=*)',
		    attrlist=['cn','monitoredInfo']
		)
        except ldap.LDAPError:
	    self.fail( "Monitor user cannot read "+monitor_suffix+" " + str(sys.exc_info()[0]) )

	if not getAttrValue(res[0],'cn'):
	    self.fail( "Monitor account should be able to see cn in cn=monitor" )
	if not getAttrValue(res[0],'monitoredInfo'):
	    self.fail( "Monitor account should be able to see monitoredInfo in cn=monitor" )

    def test_T7050_monitor_read_stats(self):
        try:
	    res = self.ldap_sys999.search_s(
	            'cn=Total,cn=Connections,'+monitor_suffix,
		    ldap.SCOPE_BASE,
		    filterstr='(objectclass=*)',
		    attrlist=['monitorCounter','modifyTimestamp']
		    )
        except ldap.LDAPError:
	    self.fail( "Monitor user cannot read cn=Total,cn=Connections,"+monitor_suffix+" " +
	            str(sys.exc_info()[0]) )

	if not getAttrValue(res[0],'monitorCounter'):
	    self.fail( "Monitor account should be able to see monitorCounter" )
	if not getAttrValue(res[0],'modifyTimestamp'):
	    self.fail( "Monitor account should be able to see modifyTimestamp" )

    def test_T8040_monitor_change_own_password(self):
        change_and_check_password(
		self,
	        'LDAPAdmin',
                ldap_sys999DN,
		self.ldap_sys999,
		None,
		'evenmoresecret' )

    def test_T8030_monitor_snooping_on_system_tree(self):
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                              self.ldap_sys999.search_s(system_suffix,ldap.SCOPE_BASE,'(objectclass=*)'))
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                              self.ldap_sys999.search_s(system_suffix,ldap.SCOPE_SUBTREE,'(objectclass=*)'))
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                              self.ldap_sys999.search_s(admin_group,ldap.SCOPE_BASE,'(objectclass=*)'))

    def test_T6060_monitor_delete_applicant(self):
        self.assertRaises(ldap.LDAPError, self.ldap_sys999.delete_s, ldap_applicant002DN)

    def test_T7030_monitor_add_entry(self):
	# Should not be able to add entries
	global entry_list
        modlist = [('objectClass', ['inetOrgPerson','mozilliansPerson']),
                    ('uniqueIdentifier', 'testnew'),
                    ('uid', 'testnew'),
                    ('cn', 'Test new user'),
                    ('givenName', 'Tess'),
                    ('sn', 'Test')]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_sys999.add_s(ldap_newuserDN, modlist))
	# Make sure that we clear this entry up afterwards
        entry_list.append(ldap_newuserDN)

class LdapReplicatorsUserTests(unittest.TestCase):

    # These tests require a system user in the Replicators group

    def setUp(self):
    	setUpCommon(self)
	# Add test user to group
	self.ldap_rootDN.modify_s(
		replicator_group,
		[ (ldap.MOD_ADD,'member',ldap_sys999DN) ]
	    )

    def tearDown(self):
	# Remove test user from group
	self.ldap_rootDN.modify_s(
		replicator_group,
		[ (ldap.MOD_DELETE,'member',ldap_sys999DN) ]
	    )
	# Now clear out test entries and close connections
    	tearDownCommon(self)

    def test_T7010_replicator_read_suffix(self):
        try:
	    res = self.ldap_sys999.search_s(
	            ldap_suffix,
		    ldap.SCOPE_BASE,
		    filterstr='(objectclass=*)',
		    attrlist=['*','+']
		)
        except ldap.LDAPError:
	    self.fail( "Replicator user cannot read "+ldap_suffix+" " + str(sys.exc_info()[0]) )

	if not getAttrValue(res[0],'objectclass'):
	    self.fail( "Replicator account should be able to see objectclass in suffix entry" )
	if not getAttrValue(res[0],'entryCSN'):
	    self.fail( "Replicator account should be able to see entryCSN in suffix entry" )

    def test_T7010_replicator_read_password(self):
	# This is the only account that should be able to read passwords
        try:
	    res = self.ldap_sys999.search_s(
	            ldap_suffix,
		    ldap.SCOPE_SUBTREE,
		    filterstr='(uid=test001)',
		    attrlist=['*','+']
		)
        except ldap.LDAPError:
	    self.fail( "Replicator user cannot find uid=test001" + str(sys.exc_info()[0]) )

	if not getAttrValue(res[0],'objectclass'):
	    self.fail( "Replicator account should be able to see objectclass in uid=test001 entry" )
	if not getAttrValue(res[0],'userPassword'):
	    self.fail( "Replicator account should be able to see userPassword in uid=test001 entry" )

    def test_T7020_replicator_read_dit(self):

	# WARNING: this will take a long time if run on a server with a lot of entries
	#          It may also cause memory exhaustion.
        try:
	    res = self.ldap_sys999.search_s(
	            ldap_suffix,
		    ldap.SCOPE_SUBTREE,
		    filterstr='(objectclass=*)',
		    attrlist=['*','+']
		    )
        except ldap.LDAPError:
	    self.fail( "Replicator user cannot enumerate the entire DIT " +
	            str(sys.exc_info()[0]) )

        # print "Got", len(res), "entries"


    def test_T7020_replicator_read_system_tree(self):
        try:
	    res = self.ldap_sys999.search_s(
	            system_suffix,
		    ldap.SCOPE_BASE,
		    filterstr='(objectclass=*)'
		    )
        except ldap.LDAPError:
	    self.fail( "Replicator user cannot read the system data at "+system_suffix+" " +
	            str(sys.exc_info()[0]) )

        try:
	    res = self.ldap_sys999.search_s(
	            monitor_group,
		    ldap.SCOPE_BASE,
		    filterstr='(objectclass=*)'
		    )
        except ldap.LDAPError:
	    self.fail( "Replicator user cannot read the system data at "+monitor_group+" " +
	            str(sys.exc_info()[0]) )
	if not getAttrValue(res[0],'member'):
	    self.fail( "Replicator account should be able to see members in system groups" )

    def test_T6060_replicator_delete_applicant(self):
        self.assertRaises(ldap.LDAPError,
                          self.ldap_sys999.delete_s,
                          (ldap_applicant002DN))

    def test_T7030_replicator_add_entry(self):
	# Should not be able to add entries
	global entry_list
        modlist = [('objectClass', ['inetOrgPerson','mozilliansPerson']),
                   ('uniqueIdentifier', 'testnew'),
                   ('uid', 'testnew'),
                   ('cn', 'Test new user'),
                   ('givenName', 'Tess'),
                   ('sn', 'Test')]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_sys999.add_s(ldap_newuserDN, modlist))

	# Make sure that we clear this entry up afterwards
        entry_list.append(ldap_newuserDN)

    def test_T8010_replicator_hack_people_node(self):
        modlist = [ (ldap.MOD_REPLACE,'description','Bad, very bad...'), ]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_sys999.modify_s(people_node, modlist))


class LdapAdminsUserTests(unittest.TestCase):

    # These tests require a system user in the Admins group

    def setUp(self):
    	setUpCommon(self)
	# Add test user to group
	self.ldap_rootDN.modify_s(
		admin_group,
		[ (ldap.MOD_ADD,'member',ldap_sys999DN) ]
	    )

    def tearDown(self):
	# Remove test user from group
	self.ldap_rootDN.modify_s(
		admin_group,
		[ (ldap.MOD_DELETE,'member',ldap_sys999DN) ]
	    )
	# Now clear out test entries and close connections
    	tearDownCommon(self)

    def test_T7010_admin_read_suffix(self):
        try:
	    res = self.ldap_sys999.search_s(
	            ldap_suffix,
		    ldap.SCOPE_BASE,
		    filterstr='(objectclass=*)',
		    attrlist=['*','+']
		)
        except ldap.LDAPError:
	    self.fail( "Admin user cannot read "+ldap_suffix+" " + str(sys.exc_info()[0]) )

	if not getAttrValue(res[0],'objectclass'):
	    self.fail( "Admin account should be able to see objectclass in suffix entry" )

    def test_T1050_admin_read_password(self):
	# Although this account can change passwords it should not be able to read them
        try:
	    res = self.ldap_sys999.search_s(
	            ldap_applicant002DN,
		    ldap.SCOPE_BASE,
		    filterstr='(objectclass=*)',
		    attrlist=['uid','userPassword']
		)
        except ldap.LDAPError:
	    self.fail( "Admin user cannot read "+ldap_applicant002DN+" " + str(sys.exc_info()[0]) )

	if not getAttrValue(res[0],'uid'):
	    self.fail( "Admin account should be able to see uid in user entry" )
	if getAttrValue(res[0],'userPassword'):
	    self.fail( "Admin account should not be able to see userPassword in user entry" )

    def test_T1030_admin_change_mozillian_password(self):
        change_and_check_password(
		self,
	        'LDAPAdmin',
                ldap_mozillian011DN,
		self.ldap_sys999,
		None,
		'evenmoresecret' )

    def test_T1030_admin_change_applicant_password(self):
        change_and_check_password(
		self,
	        'LDAPAdmin',
                ldap_applicant002DN,
		self.ldap_sys999,
		None,
		'evenmoresecret' )

    def test_T8040_admin_change_own_password(self):
        change_and_check_password(
		self,
	        'LDAPAdmin',
                ldap_sys999DN,
		self.ldap_sys999,
		None,
		'evenmoresecret' )


    def test_T2010_admin_search_mozillian(self):
	# LDAP Admin searching for a person entry
	try:
	    res = self.ldap_sys999.search_s(
		    people_node,
		    ldap.SCOPE_SUBTREE,
		    filterstr='(uid=test012)' )

	    self.assertEqual( len(res), 1,
	            "LDAP Admin search for (uid=test012) should return exactly one entry. We got "+str(len(res)) )
            # print res[0]
        except ldap.LDAPError:
	    self.fail( "LDAP Admin cannot search under "+people_node+" " + str(sys.exc_info()[0]) )

	# Check that we got values for the basic attributes
	if not getAttrValue(res[0],'objectClass'):
	    self.fail( "LDAP Admin should see the objectClass value" )
	if not getAttrValue(res[0],'cn'):
	    self.fail( "LDAP Admin should see the cn value" )
	if not getAttrValue(res[0],'givenName'):
	    self.fail( "LDAP Admin should see the givenName value" )
	if not getAttrValue(res[0],'sn'):
	    self.fail( "LDAP Admin should see the sn value" )
	if not getAttrValue(res[0],'uid'):
	    self.fail( "LDAP Admin should see the uid value" )
	if not getAttrValue(res[0],'uniqueIdentifier'):
	    self.fail( "LDAP Admin should see the uniqueIdentifier value" )
	if not getAttrValue(res[0],'mozilliansVouchedBy'):
	    self.fail( "LDAP Admin should see the mozilliansVouchedBy value" )

        # Now test to see if we got any attributes that we should not see (T1050)
	if getAttrValue(res[0],'userPassword'):
	    self.fail( "LDAP Admin should not be able to read passwords" )


    def test_T2025_admin_search_links(self):
	# LDAP Admin searching for a link entry
	try:
	    res = self.ldap_mozillian011.search_s(
		    ldap_mozillian013DN,
		    ldap.SCOPE_SUBTREE,
		    filterstr='(mozilliansServiceURI=*)' )
        except ldap.LDAPError:
	    self.fail( "LDAP Admin cannot search for link entries under "+ldap_mozillian013DN+" " + str(sys.exc_info()[0]) )

	# Check that we got values for the basic attributes
	if not getAttrValue(res[0],'objectClass'):
	    self.fail( "LDAP Admin should see the objectClass value in a link entry" )
	if not getAttrValue(res[0],'mozilliansServiceURI'):
	    self.fail( "LDAP Admin should see the mozilliansServiceURI value in a link entry" )
	if not getAttrValue(res[0],'mozilliansServiceID'):
	    self.fail( "LDAP Admin should see the mozilliansServiceID value in a link entry" )


    def test_T2020_admin_change_user_attributes(self):
        try:
	    self.ldap_sys999.modify_s(
	        ldap_mozillian012DN,
		    [
		        (ldap.MOD_REPLACE,'cn','modified CN'),
		        (ldap.MOD_REPLACE,'givenName','modified givenName'),
		        (ldap.MOD_REPLACE,'sn','modified SN'),
		        (ldap.MOD_REPLACE,'displayName','modified displayName'),
		        (ldap.MOD_REPLACE,'mail',['new@mail.one','new@mail.two']),
		        (ldap.MOD_REPLACE,'uid','modified UID'),
		        (ldap.MOD_REPLACE,'telephoneNumber',['+1 234','+5-678-90']),
		        (ldap.MOD_REPLACE,'description','modified description'),
		        (ldap.MOD_REPLACE,'jpegPhoto','modified jpegPhoto'),
		    ]
		)
        except ldap.LDAPError:
	    self.fail( "LDAP Admin cannot modify Mozillian's user atttributes " + str(sys.exc_info()[0]) )


    def test_T2030_admin_unvouch_user(self):
        try:
            modlist = [(ldap.MOD_DELETE,'mozilliansVouchedBy',None), ]
	    self.ldap_sys999.modify_s(ldap_mozillian012DN, modlist)
        except ldap.LDAPError:
	    self.fail( "LDAP Admin cannot un-vouch a user " + str(sys.exc_info()[0]) )

    # LDAP Admin is allowed to put any value into the voucher attribute
    def test_T2035_admin_revouch_user(self):
        try:
	    self.ldap_sys999.modify_s(
	        ldap_mozillian012DN,
		    [
		        (ldap.MOD_REPLACE,'mozilliansVouchedBy',ldap_mozillian012DN),
		    ]
		)
        except ldap.LDAPError:
	    self.fail( "LDAP Admin cannot un-vouch a user " + str(sys.exc_info()[0]) )

    # LDAP Admin is allowed to delete user entries completely
    def test_T2040_admin_delete_user(self):
        try:
	    self.ldap_sys999.delete_s(ldap_mozillian012DN)
        except ldap.LDAPError:
	    self.fail( "LDAP Admin cannot delete a user " + str(sys.exc_info()[0]) )

    # LDAP Admin is allowed to delete link entries completely
    def test_T2025_admin_delete_linkentry(self):
        try:
	    self.ldap_sys999.delete_s(ldap_link013DN)
        except ldap.LDAPError:
	    self.fail( "LDAP Admin cannot delete a link entry " + str(sys.exc_info()[0]) )

    def test_T2025_admin_add_links(self):
	try:
	    self.ldap_sys999.add_s(
		    ldap_link011aDN,
		    [
			('objectClass', 'mozilliansLink'),
			('uniqueIdentifier', 'a'),
			('mozilliansServiceURI', 'irc://irc.mozilla.org/'),
			('mozilliansServiceID', 'testeleven')
		    ]
		)
	    # Make sure that we clear this entry up afterwards
	    entry_list.append(ldap_link011aDN)
        except ldap.LDAPError:
	    self.fail( "LDAP Admin cannot add link entry "+ldap_link011aDN+" " + str(sys.exc_info()[0]) )

    def test_T2025_admin_manage_links(self):
        try:
	    self.ldap_sys999.modify_s(
		    ldap_link013DN,
		    [
			(ldap.MOD_REPLACE,'mozilliansServiceID','test-new-thirteen')
		    ]
		)
        except ldap.LDAPError:
	    self.fail( "LDAP Admin cannot modify link entry "+ldap_link013DN+" " + str(sys.exc_info()[0]) )


    # LDAP Admin is allowed to add new user entries
    def test_T2060_admin_add_user(self):
	global entry_list

        try:
	    self.ldap_sys999.add_s(
	            ldap_newuserDN,
                    [
		        ('objectClass', ['inetOrgPerson','mozilliansPerson']),
			('uniqueIdentifier', 'testnew'),
			('uid', 'testnew'),
			('cn', 'Test new user'),
                        ('givenName', 'Tess'),
			('sn', 'Test')
		    ]
		)
	    # Make sure that we clear this entry up afterwards
	    entry_list.append(ldap_newuserDN)
        except ldap.LDAPError:
	    self.fail( "LDAP Admin cannot add a user " + str(sys.exc_info()[0]) )

    def test_T2060_admin_add_bad_user_entry(self):
	# Should not be able to add entries with the wrong objectclass
	# (mozilliansObject in place of mozilliansPerson in this case)
	global entry_list
        modlist = [('objectClass', ['inetOrgPerson','mozilliansObject']),
                    ('uniqueIdentifier', 'testnew'),
                    ('uid', 'testnew'),
                    ('cn', 'Test new user'),
                    ('givenName', 'Tess'),
                    ('sn', 'Test')]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_sys999.add_s(ldap_newuserDN, modlist))
	# Make sure that we clear this entry up afterwards
        entry_list.append(ldap_newuserDN)


    def test_T2050_admin_hack_sys_password(self):
	self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_sys999.passwd_s(ldap_sys900DN, None, 'owned!'))


    def test_T8010_admin_hack_people_node(self):
        modlist = [(ldap.MOD_REPLACE,'description','Bad, very bad...'), ]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_sys999.modify_s(people_node, modlist))

    def test_T8030_ldapadmin_snooping_on_system_tree(self):
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                              self.ldap_sys999.search_s(system_suffix,ldap.SCOPE_BASE,'(objectclass=*)'))

        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                              self.ldap_sys999.search_s(system_suffix,ldap.SCOPE_SUBTREE,'(objectclass=*)'))
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                              self.ldap_sys999.search_s(admin_group,ldap.SCOPE_BASE,'(objectclass=*)'))
	# Should not even see its own entry
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                              self.ldap_sys999.search_s(ldap_sys999DN,ldap.SCOPE_BASE,'(objectclass=*)'))

    def test_T9026_admin_change_table_data(self):
        try:
	    self.ldap_sys999.modify_s(
	        ldap_table_entry_DN,
		    [
		        (ldap.MOD_REPLACE,'textTableValue','Modified by admin'),
		    ]
		)
        except ldap.LDAPError:
	    self.fail( "LDAP Admin cannot modify table data " + str(sys.exc_info()[0]) )

    def test_T9026_admin_add_table_data(self):
	try:
	    self.ldap_sys999.add_s(
		    ldap_table_new_entry_DN,
		    [
			('objectClass', 'textTableEntry'),
			('textTableKey', 'a'),
			('textTableValue', 'new data'),
		    ]
		)
	    # Make sure that we clear this entry up afterwards
	    entry_list.append(ldap_table_new_entry_DN)
        except ldap.LDAPError:
	    self.fail( "LDAP Admin cannot add table entry "+ldap_table_new_entry_DN+" " + str(sys.exc_info()[0]) )


    def test_T2070_ldapadmin_read_all_accounts(self):

	# WARNING: this will take a long time if run on a server with a lot of entries
	#          It may also cause memory exhaustion.
        try:
	    res = self.ldap_sys999.search_s(
	            people_node,
		    ldap.SCOPE_SUBTREE,
		    filterstr='(objectclass=*)',
		    attrlist=['*','+']
		    )
        except ldap.LDAPError:
	    self.fail( "LDAP Admin cannot enumerate the whole set of users " +
	            str(sys.exc_info()[0]) )


class RegistrationAgentTests(unittest.TestCase):

    # These tests require a system user in the RegistrationAgent group

    def setUp(self):
    	setUpCommon(self)
	# Add test user to group
	self.ldap_rootDN.modify_s(
		regAgent_group,
		[ (ldap.MOD_ADD,'member',ldap_sys999DN) ]
	    )

    def tearDown(self):
	# Remove test user from group
	self.ldap_rootDN.modify_s(
		regAgent_group,
		[ (ldap.MOD_DELETE,'member',ldap_sys999DN) ]
	    )
	# Now clear out test entries and close connections
    	tearDownCommon(self)

    def test_T7010_regAgent_read_suffix(self):
        try:
	    res = self.ldap_sys999.search_s(
	            ldap_suffix,
		    ldap.SCOPE_BASE,
		    filterstr='(objectclass=*)',
		    attrlist=['*','+']
		)
        except ldap.LDAPError:
	    self.fail( "regAgent user cannot read "+ldap_suffix+" " + str(sys.exc_info()[0]) )

	if not getAttrValue(res[0],'objectclass'):
	    self.fail( "regAgent account should be able to see objectclass in suffix entry" )

    def test_T1050_regAgent_read_password(self):
	# Although this account can change passwords it should not be able to read them
        try:
	    res = self.ldap_sys999.search_s(
	            ldap_applicant002DN,
		    ldap.SCOPE_BASE,
		    filterstr='(objectclass=*)',
		    attrlist=['uid','userPassword']
		)
        except ldap.LDAPError:
	    self.fail( "regAgent user cannot read "+ldap_applicant002DN+" " + str(sys.exc_info()[0]) )

	if not getAttrValue(res[0],'uid'):
	    self.fail( "regAgent account should be able to see uid in user entry" )
	if getAttrValue(res[0],'userPassword'):
	    self.fail( "regAgent account should not be able to see userPassword in user entry" )

    def test_T1030_regAgent_change_mozillian_password(self):
        change_and_check_password(
		self,
	        'regAgent',
                ldap_mozillian011DN,
		self.ldap_sys999,
		None,
		'evenmoresecret' )

    def test_T1030_regAgent_change_applicant_password(self):
        change_and_check_password(
		self,
	        'regAgent',
                ldap_applicant002DN,
		self.ldap_sys999,
		None,
		'evenmoresecret' )

    def test_T8040_regAgent_change_own_password(self):
        change_and_check_password(
		self,
	        'LDAPregAgent',
                ldap_sys999DN,
		self.ldap_sys999,
		None,
		'evenmoresecret' )


    def test_T3060_regAgent_search_mozillian(self):
	# regAgent searching for a person entry
	try:
	    res = self.ldap_sys999.search_s(
		    people_node,
		    ldap.SCOPE_SUBTREE,
		    filterstr='(uid=test012)' )

	    self.assertEqual( len(res), 1,
	            "regAgent search for (uid=test012) should return exactly one entry. We got "+str(len(res)) )
            # print res[0]
        except ldap.LDAPError:
	    self.fail( "regAgent cannot search under "+people_node+" " + str(sys.exc_info()[0]) )

	# Check that we got values for the basic attributes
	if not getAttrValue(res[0],'objectClass'):
	    self.fail( "regAgent should see the objectClass value" )
	if not getAttrValue(res[0],'cn'):
	    self.fail( "regAgent should see the cn value" )
	if not getAttrValue(res[0],'givenName'):
	    self.fail( "regAgent should see the givenName value" )
	if not getAttrValue(res[0],'sn'):
	    self.fail( "regAgent should see the sn value" )
	if not getAttrValue(res[0],'uid'):
	    self.fail( "regAgent should see the uid value" )
	if not getAttrValue(res[0],'uniqueIdentifier'):
	    self.fail( "regAgent should see the uniqueIdentifier value" )
	if not getAttrValue(res[0],'mozilliansVouchedBy'):
	    self.fail( "regAgent should see the mozilliansVouchedBy value" )

        # Now test to see if we got any attributes that we should not see (T1050)
	if getAttrValue(res[0],'userPassword'):
	    self.fail( "regAgent should not be able to read passwords" )


    def test_T3040_regAgent_change_user_attributes(self):
	# This should fail because it involves deleting a value as well as adding a new one
        modlist = [(ldap.MOD_REPLACE,'cn','modified CN'),]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_sys999.modify_s(ldap_mozillian012DN, modlist))


    def test_T2030_regAgent_unvouch_user(self):
	# We may permit the regAgent to vouch for users
	# but we do not allow it to un-vouch
        modlist = [(ldap.MOD_DELETE,'mozilliansVouchedBy',None), ]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_sys999.modify_s(ldap_mozillian012DN, modlist))
                           

    def test_T6060_replicator_delete_applicant(self):
	# LDAP regAgent is not allowed to delete user entries
        self.assertRaises(ldap.LDAPError,
                          self.ldap_sys999.delete_s,
                          (ldap_applicant002DN))

    # regAgent is allowed to add new user entries
    def test_T3010_regAgent_add_user(self):
	global entry_list

        try:
	    self.ldap_sys999.add_s(
	            ldap_newuserDN,
                    [
		        ('objectClass', ['inetOrgPerson','mozilliansPerson']),
			('uniqueIdentifier', 'testnew'),
			('uid', 'testnew'),
			('cn', 'Test new user'),
                        ('givenName', 'Tess'),
			('sn', 'Test')
		    ]
		)
	    # Make sure that we clear this entry up afterwards
	    entry_list.append(ldap_newuserDN)
        except ldap.LDAPError:
	    self.fail( "LDAP regAgent cannot add a user " + str(sys.exc_info()[0]) )

    # regAgent is allowed to add new user entries that are pre-vouched
    # It may set the password as well, but we would not normally do that by
    # writing direct to the userPassword attribute like this test does
    def test_T3020_regAgent_add_prevouched_user(self):
	global entry_list

        try:
	    self.ldap_sys999.add_s(
	            ldap_newuserDN,
                    [
		        ('objectClass', ['inetOrgPerson','mozilliansPerson']),
			('uniqueIdentifier', 'testnew'),
			('uid', 'testnew'),
			('cn', 'Test new user'),
                        ('givenName', 'Tess'),
			('sn', 'Test'),
			('mozilliansVouchedBy', ldap_mozillian012DN),
			('userPassword','notverysecret')
		    ]
		)
	    # Make sure that we clear this entry up afterwards
	    entry_list.append(ldap_newuserDN)
        except ldap.LDAPError:
	    self.fail( "LDAP regAgent cannot add a user " + str(sys.exc_info()[0]) )

    def test_T3010_regAgent_add_bad_user_entry(self):
	# Should not be able to add entries with the wrong objectclass
	# (mozilliansObject in place of mozilliansPerson in this case)
	global entry_list
        modlist = [('objectClass', ['inetOrgPerson','mozilliansObject']),
                   ('uniqueIdentifier', 'testnew'),
                   ('uid', 'testnew'),
                   ('cn', 'Test new user'),
                   ('givenName', 'Tess'),
                   ('sn', 'Test') ]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_sys999.add_s(ldap_newuserDN, modlist))

	# Make sure that we clear this entry up afterwards
        entry_list.append(ldap_newuserDN)


    def test_T3050_regAgent_delete_applicant(self):
        self.assertRaises(ldap.INSUFFICIENT_ACCESS,
                          self.ldap_sys999.delete_s,
                          (ldap_applicant002DN))


    def test_T2050_regAgent_hack_sys_password(self):
	self.assertRaises(ldap.INSUFFICIENT_ACCESS, lambda:\
                          self.ldap_sys999.passwd_s(ldap_sys900DN, None, 'owned!'))


    def test_T8010_regAgent_hack_people_node(self):
        modlist = [ (ldap.MOD_REPLACE,'description','Bad, very bad...'), ]
        self.assertRaises(ldap.INSUFFICIENT_ACCESS, 
                          lambda:\
                              self.ldap_sys999.modify_s(people_node, modlist))


    def test_T8030_regAgent_snooping_on_system_tree(self):
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                              self.ldap_sys999.search_s(system_suffix, ldap.SCOPE_BASE, '(objectclass=*)'))
                          
            
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                              self.ldap_sys999.search_s(system_suffix, ldap.SCOPE_SUBTREE, '(objectclass=*)'))

            
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                              self.ldap_sys999.search_s(admin_group,ldap.SCOPE_BASE,'(objectclass=*)'))
            
	# Should not even see its own entry
        self.assertRaises(ldap.NO_SUCH_OBJECT, lambda:\
                              self.ldap_sys999.search_s(ldap_sys999DN,ldap.SCOPE_BASE,'(objectclass=*)'))



class TableManagerTests(unittest.TestCase):

    # These tests require a system user in the temporary test group

    def setUp(self):
    	setUpCommon(self)
	# Add test user to group
	self.ldap_rootDN.modify_s(
		test_group,
		[ (ldap.MOD_ADD,'member',ldap_sys999DN) ]
	    )

    def tearDown(self):
	# Remove test user from group
	self.ldap_rootDN.modify_s(
		test_group,
		[ (ldap.MOD_DELETE,'member',ldap_sys999DN) ]
	    )
	# Now clear out test entries and close connections
    	tearDownCommon(self)


    def test_T9026_manager_change_table_data(self):
        try:
	    self.ldap_sys999.modify_s(
	        ldap_table_entry_DN,
		    [
		        (ldap.MOD_REPLACE,'textTableValue','Modified by admin'),
		    ]
		)
        except ldap.LDAPError:
	    self.fail( "Table manager cannot modify table data " + str(sys.exc_info()[0]) )

    def test_T9026_manager_add_table_data(self):
	try:
	    self.ldap_sys999.add_s(
		    ldap_table_new_entry_DN,
		    [
			('objectClass', 'textTableEntry'),
			('textTableKey', 'a'),
			('textTableValue', 'new data'),
		    ]
		)
	    # Make sure that we clear this entry up afterwards
	    entry_list.append(ldap_table_new_entry_DN)
        except ldap.LDAPError:
	    self.fail( "Table manager cannot add table entry "+ldap_table_new_entry_DN+" " + str(sys.exc_info()[0]) )

########################################################################
# Main program
########################################################################

if __name__ == '__main__':
    unittest.main()

