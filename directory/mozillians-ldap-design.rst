############################################################
Design Document: LDAP tree and schema for mozillians.org
############################################################

Release 1.0 supports a fairly basic addressbook function.

User entries are based on inetOrgPerson plus an auxiliary objectclass
called *mozilliansPerson*

As far as possible, the LDAP design avoids creating new attributes -
particularly attributes specific to individual remote services (bugzilla, twitter, etc)

Later releases need an expandable store for servicename:ID tuples.
These will be implemented as entries beneath the main user entry.

The *Privacy Release* needs the ability for each user to control the
visibility of each item of data individually.
For tuples this will simply mean controlling the visibility of the sub-entry.
Any attributes used in the main entry will have to be special-cased in the ACLs, so keeping
them to a minimum is good. On the other hand, we want the main entry to
be usable by other LDAP-aware apps, so it should not look too different
from a normal inetOrgPerson.  Apps will have to cope with getting no data
for mandatory attributes like cn. This has always been true for LDAP,
but some existing apps may not be robust in this respect as most LDAP services
adopt an all-or-nothing approach to access-control.

It will be an early requirement to have test data and ACLs that exercise
a variety of data-visibility scenarios so that devs can be sure that
code is robust when no data is provided.

Tags will not be in 1.0 - probably will be in Security Release,
and probably implemented as LDAP groups. One use-case is to list all
members with a specific tag. This would be inefficient if done using
basic LDAP commands and no server-side support, so we may need to enable
the memberOf overlay (note that this acts at create/modify time rather
than during search, so must turn it on before creating any groups).

Most tags will be open for people to associate with, but some will be
"blessed" in the sense that they can only be awarded to users by a defined list of people.
That list will probably be defined by the possession of another tag.

==================
Authentication
==================

The plan here is to have the middleware bind to LDAP using the user's own ID and password.
This allows LDAP to control who may do/see stuff,
and prevents total compromise if the middleware gets cracked.

We should probably require TLS on the LDAP session.
ACLs could enforce this if necessary, but that might exclude less-capable LDAP clients later
(though this may be considered good :-))

Note that an LDAP 'username' is always in the form of a DN.
This means that e-mail addresses cannot be directly used as usernames.
The normal approach is to store a conventional username in the *uid*
attribute and then follow this sequence:

* Bind to LDAP anonymously (or as a specific system ID)
* Search for (uid=username)
* Fail if we do not get exactly one entry
* Take the DN of the entry we found and try to bind as that, with the supplied password.

A possible alternative is to use SASL PLAIN authentication after starting TLS.
The LDAP server is able to search for the asserted username in any
attribute chosen by the server admin (usually the uid attribute).
This avoids the client having to do an extra search at the start of the
session, but at the cost of requiring clients to support SASL.
It also allows the uid attribute to be completely protected against anon search
if desired.

---------------------------------
Username considerations
---------------------------------

Usernames will show up in URLs, so the form chosen should be clean in that environment.

Usernames cannot be completely hidden from public view,
so they should not expose data that the user would prefer to keep hidden.

In fact we could leave the choice of username entirely to the users:
explain the consequences and let them change it at any time.
The account will be referred to internally by DN, using something like a
sequence number as the identifier so very little info is exposed by that.

Anyone who changes their username will break existing profile URL pointers
in web pages.
That might be exactly what they want.

Developers should be aware that LDAP uses the UTF-8 character set
for almost all attributes, so it is possible that a user might choose a username
like 'Åke', or even something in Arabic script or Kanji.

===================
Search Limits
===================

The target community is ~100,000 people. We don't want searches to return that
sort of number of entries (for all sorts of reasons),
so the LDAP server will enforce limits.

What is a good limit?
This depends on the use-cases, but if data is for human
consumption then 100 entries is plenty.

If a search matches more entries than the limit allows, then the
client app will get 100 plus an 'admin limit exceeded' error code.
Note that this might confuse apps that try to treat LDAP like a relational DB.
Note also that the common Python LDAP search command treats this case
as an error and does not even return the 100 entries that it received. See
http://www.python-ldap.org/doc/html/ldap-async.html for an appropriate way to handle this.

To make sure that the mozillians.org code is robust in this case
the development server will have a fairly large set of test data
and a relatively low search limit.

==================
Vouching
==================

User accounts are expected to follow this lifecycle:

#. Anonymous web user requests an account, giving an e-mail address.
#. A verification token is mailed to that address (this provides some
   measure of accountability and limits account-spam)
#. User presents the token to validate the account.
   This makes it eligible for vouching and visible to existing Mozillians.
#. User requests an existing Mozillian to vouch for them.
#. Mozillian inspects the new user entry and (if they approve)
   writes their own entry DN into the *mozilliansVouchedBy* attribute.
   The new user is now a Mozillian.

Accounts that do not get vouched for within a reasonable length of time
should be removed by an automatic process.

By storing the DN of the vouching user in the entry of the vouchee we get a neat bit of accountability.

====================
Admin accounts
====================

The people who administer the LDAP service need access beyond what
is granted to normal users.
The system itself needs accounts for special purposes too.

Rather than providing one account for each role, the design gives power
to LDAP groups. An example account is provided for each group, but
in principle any user can be given any power simply by adding them
to the appropriate group.

In practice it is not wise to give special powers to ordinary (Mozillian)
accounts, so the administrative accounts are held in a separate part
of the tree that is normally invisible.

-------------------
LDAP Admins
-------------------

There need to be people who can sort out errors, kick out baddies etc.
They should be able to do all that,
but should not be able to wreak total destruction on the LDAP tree if it can be avoided.

-------------------
Registration Agent
-------------------

We cannot allow anon users to create accounts, as we would get spammed.
There needs to be some level of accountability, e.g. by tying the
account-creation process to an e-mail address as in the lifecycle above.
Another option is to require a Turing Test such as a CAPTCHA.
LDAP cannot enforce this on
its own so there needs to be an agent to do it, and that agent will need
special permission to create accounts. The agent thus needs an account
of its own so that the ACLs can identify it.

We could set things up so that the registration agent cannot set the
'vouched' flag: thus even if it gets hacked it cannot create visible
accounts on its own.
Unfortunately this would probably conflict with the Invitation feature
so the current implementation allows the registration agent to put
any DN into the *mozilliansVouchedBy* attribute.

--------------------
Replicator
--------------------

There will be multiple LDAP servers holding identical data.
To keep them in sync there is a replication protocol.
The account(s) used by that protocol need access to more data
than we will expose to normal users.

--------------------
Monitors
--------------------

LDAP servers make available some statistical data about their workload.
We may not wish to expose that data to the world at large,
so it is restricted to a defined set of accounts.


===============================================
The DIT (Directory Information Tree)
===============================================

* dc=mozillians,dc=org        - This is the LDAP suffix. It may be different if other people deploy the code

 * ou=people                  - Container for user account
 * ou=tags                    - (future) container for tag data
 * ou=tables                  - Container for lookup tables
 * ou=system                  - Container for system data (may not be visible to normal users)

   * ou=accounts              - Container for system accounts
   * ou=groups                - Container for system groups
   * ou=policies              - Container for password policies etc

===============================================
Attributes and Object Classes
===============================================

All attribute and objectclass names created for this project start
*mozillians* to avoid clashes with others.

All OIDs are be based on 1.3.6.1.4.1.13769.3000
See https://wiki.mozilla.org/LDAP_OID for the background to this

===============================================
User Accounts
===============================================

These are based on the inetOrgPerson objectclass,
as all common LDAP clients understand that.
We use a subset of the available attributes,
and this is enforced by access-control rules.

We extend the class as needed using the *mozilliansPerson* auxiliary class.

Entries are named using the *uniqueIdentifier* attribute:
its value is opaque and it will not have any meaning outside the DIT.
This allows usernames (*uid* attribute) to be changed without affecting group membership etc.
It also avoids exposing sensitive information in DNs, which are very hard to hide.

Entries will never be renamed. *uniqueIdentifier* values will never be reused.

--------------------------------
Attributes for user accounts
--------------------------------

* cn (MUST)
* displayName - a copy of the preferred cn value
* sn (MUST)
* objectClass (MUST)
* uid (MUST because this is the username known to the user)
* userPassword (SSHA hashed, not readable by anyone)
* uniqueIdentifier (MUST because this is the LDAP naming attribute)
* mail
* telephoneNumber
* jpegPhoto
* description - this would hold the Bio
* mozilliansVouchedBy


Some attributes will be required to have unique values, e.g. *uid* and *uniqueIdentifier*

All text attributes are in the UTF-8 character set
(except for a few more restrictive ones like mail)

.......................................
Duplication of data in user entries
.......................................

Identical values may appear in multiple attributes.
This may seem to be wasteful and against the principle of normalisation,
but the reason is that each attribute serves a different purpose and thus in
some cases may need a different value.

An example of this is *cn* and *displayName* which will contain identical data
in most entries. *cn* is used for searching, so it may have multiple values
whereas *displayName* is used only for display and must have a single value.

Another example is the mail address, which may appear in *mail* (as an informational
attribute) and also in *uid* where it is being used as a username.
Keeping the two concepts separate allows for a user to change their username
without changing their e-mail address and vice-versa.

=================================
Link entries
=================================

Mozillians.org allows people to record links to their IDs on other services.
For each link there is a servicename:ID tuple, which is represented as *mozilliansLink*
entry immediately beneath the user's main entry.

Each link entry contains two important attributes:

mozilliansServiceURI
    This is a URI representing the remote service

mozilliansServiceID
    This is the person's visible identifier on the remote service.
    Note that it may not be the same as the username that they use to login with.

A *displayName* attribute is also allowed, in case the user wants to label the
accountin some way (e.g. "My admin account" vs "My test account").

Link entries are named with the *uniqueIdentifier* attribute.
The value of this has no specific meaning.
A convenient value would be the precise time of creation of the entry
(e.g. 'date +%s.%N' output)


=================================
Lookup Tables
=================================

Most applications need lookup tables.
An example in the mozillians.org project is the list of linked services.
Although there is no intention to restrict the services that can be linked to,
it will be convenient for users if a list of common services is provided,
perhaps as a drop-down menu.

In LDAP, tabular data is represented as a one-level tree of entries
as described in RFC2293.
For text tables, the mapping is between the attributes *textTableKey* and *textTableValue*
The *textTableKey* attribute is conventionally used as the naming attribute.

One table has been provided in the initial data:
cn=linked services,ou=tables,dc=mozillians,dc=org
It is modifiable by any member of the LDAP Managers group,
and can be searched by anyone.

=================================
Access Control Rules
=================================

The 1.0 release has fairly simple requirements as there are no tags.

These are the main principals who may access the directory:

* rootDN - the all-powerful LDAP admin. Only used during setup. Not subject to any form of access control.
* LDAPAdmin - very powerful admin account
* Monitor - account used for routine monitoring of servers
* Replicator - account used by replication consumers (slave LDAP servers)
* regAgent - the registration agent
* Mozillian - a user who has been vouched for
* Applicant - a user who has not been vouched for
* Anon - anyone who has not authenticated to LDAP

These are the types of entry that may be accessed:

* suffix - the entry at dc=mozillians,dc=org
* public structure - non-leaf entries such as ou=people and ou=tags
* system - entries that are used by the system for internal purposes
* Mozillian - a user who has been vouched for
* Applicant - a user who has not been vouched for

Within user entries (both Applicant and Mozillian) there are attributes
that can be modified by the owner of the entry. These are the
'user-modifiable attributes'. The current list is:

* cn
* displayName
* sn
* uid (if we allow people to change their username after registering)
* mail
* telephoneNumber
* jpegPhoto
* description

Some of these attributes are subject to further rules on their content.

---------------------
The rules:
---------------------

Note that some of these overlap. Clarity is important here, minimalism is not.

The 'T' codes are cross-references to the ACL test suite

 * T0020 Anon may search under ou=people to locate an entry by uid
 * T0030 Anon may receive at most 2 results to any search (this is enough for an LDAP client to be sure that it has located the correct entry for authentication)
 * T0020 Anon may see the DN and uniqueIdentifier attribute of the entries returned by search, but no other attributes.
 * T0005 Anon may authenticate.
 * T0010 Anon may read the root DSE and the schema
 * T0015 Anon may read the dc=mozillians,dc=org (suffix) entry
 * T0016 Anon may read the ou=people,dc=mozillians,dc=org entry
 * T0040 Anon may not do or see anything else.

 * All authenticated users may do everything that Anon can do.
 * ??? Should we require crypto protection for authentication ???

 * T1010 Mozillians and Applicants may change their own passwords
 * T1020 Mozillians and Applicants may not change other users passwords
 * T1030 LDAPadmins may change passwords for any Mozillian or Applicant
 * ??? How do we deal with lost passwords ??? https://bugzilla.mozilla.org/show_bug.cgi?id=665854
 * T1050 Passwords may not be read by anyone (except rootDN and Replicator)

 * T2010 LDAPAdmin may read everything in all user and tag entries (except passwords)
 * T2020 ??? LDAPAdmin may change all user-modifiable attributes in user entries ???
 * T2030 LDAPAdmin may delete the value of the mozilliansVouchedFor attribute of any user
 * T2035 ??? LDAPAdmin may write any value into the mozilliansVouchedFor attribute of any user ???
 * T2040 ??? LDAPAdmin may remove user entries entirely ???
 * T2050 LDAPAdmin cannot see or modify any entries in the system tree
 * T2060 ??? LDAPAdmin may add new user entries

 * T3010 regAgent may create new entries directly under ou=People - these must be inetOrgPerson/mozilliansPerson entries.
 * T3020 regAgent may populate certain attributes when creating entries: all user-modifiable attributes plus uniqueIdentifier, userPassword and objectClass
 * T3030 regAgent may set mozilliansVouchedBy (this is to support invitations)
 * T3040 regAgent may not delete attribute values in existing entries
 * T3050 regAgent may not delete existing entries (??? this would prevent the regAgent account from being used to expire old un-vouched applicant entries???)
 * T3060 ??? regAgent may read all user attributes except password

 * T5010 Mozillians may write their own DN into the mozilliansVouchedBy attribute of any Applicant
 * T5020 Nobody may change the value of mozilliansVouchedBy in their own entry
 * T5030 Applicants may not vouch for each other

 * T6010 Mozillians and Applicants may change the values of any user-modifiable attributes in their own entry
 * T6020 Mozillians and Applicants may read all attributes in their own entry
 * Mozillians can receive up to 50 [?? discuss number ??] results to a search
 * T6030 Mozillians may read all attributes (except password) in other users' entries (this will change in Privacy Release)
 * T6040 Applicants may not read anything apart from their own entry
 * T6050 Applicants may search to the same extent that Anon can (though they can recieve as many entries as a Mozillian would get, there are no attributes disclosed)
 * T6060 Mozillians and Applicants cannot delete any user entries (not even their own)
 * T6070 Mozillians and Applicants cannot create new user entries

 * T7010 Replicator may read the entire content of all entries (including passwords) in the entire tree under dc=mozillians,dc=org
 * T7020 Replicator is not subject to size or time limits on searches
 * T7030 Replicator cannot add or modify user entries
 * T7050 Members of the Monitor group may read the server monitoring data, but others may not

 * T8010 Nobody other than the rootDN may modify the suffix entry, the public structure, or the system entries
 * Nobody other than the rootDN may access the LDAP server config in any way
 * T8030 Nobody other than the rootDN and Replicators may access the ou=system part of the DIT
 * T8040 System accounts can change their own passwords

 * T9010 Certain attributes must have values that are unique across all entries: uid

 * T9020 All authenticated users may read and search all lookup tables
 * T9024 Anon may not read or search lookup tables
 * T9025 Mozillians and Applicants may not change the content of any lookup tables
 * T9026 Any member of the manager group for a table may change the content

 * Anything not already mentioned above is prohibited


