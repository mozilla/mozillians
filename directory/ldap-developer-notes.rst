#################################################################
Notes for Developers on working with the Mozillians LDAP service
#################################################################

The main data store for mozillians.org is an LDAP directory.
This was chosen because it provides standards-based storage for
contact information, and because it has a rich set of access-control
features to protect the privacy of personal data.

The exact form and behaviour of the LDAP store is likely to
evolve during the project, in particular when Tags and enhanced privacy
are added in the second feature release.
The notes here suggest access and usage patterns that should be robust
in the face of these changes.

------------------------------------
The shape of the DIT
------------------------------------

In LDAP, the DIT (Directory Information Tree) is the large-scale structure
for the data.
It supports an unlimited depth of hierarchy, but in this design
we are keeping things very simple.
For release 1.0 there is only one branch that matters: the *people* branch:

* dc=mozillians,dc=org
  * ou=people

Every human user of the system will have an entry directly under *ou=people*
Some system agents also have entries, but they are normally invisible.

In LDAP terminology, the absolute name of an entry is its DN (Distinguished Name),
which consists of the catenation of all of the RDNs (Relative Distinguished Names)
up to the root. This is very similar to the way filenames are constructed in Unix.

In our case, *dc=mozillians,dc=org* is the *suffix* - meaning that it appears at the end
of every DN in the system.
The DN of the people entry is *ou=people,dc=mozillians,dc=org* and this is a good place to start
when searching for people.

---------------------------------------------
People entries
---------------------------------------------

Here is a sample entry:

| dn: uniqueIdentifier=7f3a67u000000,ou=people,dc=mozillians,dc=org
| objectclass: inetOrgPerson
| objectclass: person
| objectclass: mozilliansPerson
| displayName: Scott Wingfield
| cn: Scott Wingfield
| sn: Wingfield
| uniqueIdentifier: 7f3a67u000000
| uid: u000000
| mail: u000000@mozillians.org
| telephoneNumber: +44 1234 567000

The format above is LDIF - the LDAP Data Interchange Format (RFC2849).
The first line gives the DN of the entry.
The rest of the lines contain attribute-value data.

*objectclass* is a required attribute which describes the basic type of the entry.
In this application, the objectclass will always include *inetOrgPerson* and *mozilliansPerson*.

Descriptive attributes include *cn* (Common Name), *sn* (Surname) and *displayName*.

*uid* is normally used to store the username known to the entry owner.
There is also a *userPassword* attribute, but that is never shown.

The sample entry also contains some informational attributes: mail address and
phone number in this case.

*uniqueIdentifier* is an opaque attribute used to name the entry.
It has no meaning outside the Mozillians LDAP store.
This avoids exposing potentially sensitive information in the DN (which can appear in
many places, and is very hard to hide).
Note that the *uniqueIdentifier* attribute in the entry must match the
value used in the DN.


..........................................
Multi-valued attributes
..........................................

Most attributes in LDAP are able to store multiple values, e.g.:

| dn: uniqueIdentifier=ab04bc7a8943fa,ou=people,dc=mozillians,dc=org
| objectclass: inetOrgPerson
| objectclass: person
| objectclass: mozilliansPerson
| displayName: Andrew Findlay
| cn: A Findlay
| cn: Andrew Findlay
| cn: Findlay Andrew
| cn: Dr Andrew J Findlay BSc PhD MIET CEng
| sn: Findlay
| uniqueIdentifier: ab04bc7a8943fa
| uid: ajf
| mail: andrew.findlay@skills-1st.co.uk
| mail: andrew@findlay.org

This is perhaps an extreme example, but it server to illustrate the sort of data
that you might find.

*cn* is commonly used for searching, so in many LDAP stores it is normal practice
to have several variations on the person's name to make it easier to find.
People who are commonly known by a nickname may well put that in the *cn* attribute
alongside their 'real' name.

One consequence of multi-valued *cn* entries is that an application wishing to display
the entry does not know which value to use in the title.
LDAP attributes are *sets*, not *sequences* so there is no guarantee that they
will come out in the same order every time (though in practice they usually do).
The problem is solved by the *displayName* attribute, which is normally set to
whatever name form the person prefers to known as.
*displayName* is only allowed to have a single value.

Note that in this example there are two mali addresses.
This is not generally a good idea, as there is no way to indicate what each one
should be used for.
mozillians.org will address the multiple-accounts issue in a later release.

..........................................
Consequences of access-control
..........................................

Although the LDAP standard requires some attributes to be present in an entry,
this is no guarantee that they will be visible.
The Privacy Release will add fine-grained access control to allow each person
to limit who may see each attribute.
Applications should therefore be prepared to receive search results with few (or no) attributes
populated.

When access to an attribute is denied, LDAP behaves as if it simply does not exist.
Further, LDAP does not support the concept of null values: if an attribute is given an empty value
it is the same as removing the attribute entirely.

..........................................
Interpreting attribute values
..........................................

Most attributes used in mozillians.org are simple text strings encoded in UTF-8.
This allows them to support almost any character, accent, or diacritical mark found
anywhere in the world (including right-to-left languages like Arabic, so beware!)

Some attributes have specific requirements.
The main ones that we are concerned with are:

*mail*
    The e-mail address of a person, without any descriptive text string.
    E-mail addresses are constrained to the IA5 character set (7-bit ASCII).

*telephoneNumber*
    LDAP understands the format of telephone numbers so it is able to support
    search and match even when people add hyphens in different places.
    Telephone numbers must always be stored in full international format:

    +44 1628 782565
    +1 650 903 0800

    Attempts to be 'helpful' by adding in local-use-only prefixes should be avoided:

    +44 (0) 1628 782565

    This is bad because the interpretation is ambiguous and often country-specific.

    It is up to the user-interface to present the number to the user in a form
    that they find useful.
    It is probably reasonable to assume that Mozillians are clued-up about
    using international numbers, so no conversions need be applied for display.

----------------------------------------------------
Connecting to the LDAP server
----------------------------------------------------

There will be at least two LDAP servers when mozillians.org goes into production.
It is likely that one will be a read/write master and the rest will be read-only copies.
The exact configuration and naming has yet to be decided, but it is likely that
the slaves will be set up to relay update requests to the master so that client applications
do not need to be aware of which server has which role.
One consequence of this is that under certain failure conditions a client application
may be able to search and read, but will get errors if it attempts to update the directory.

.........................................
Making the connection
.........................................

Most LDAP client libraries support connection by URL, so app config should support
strings of the form:

* ldap://ldap.mozillians.org:389/

Depending on how we decide to handle fallback to standby servers, it may be necessary
to support lists of URLS:

* ldap://ldap1.mozillians.org:389/ ldap://ldap2.mozillians.org:389/

.........................................
Security
.........................................

The LDAP session is initially bound as the anonymous user.
This gives very little access to the data, so most client apps will want to bind
as a real user very early in the session.

Binding as a user normally involves supplying a password in clear text,
so before going any further it is wise to add an encryption layer.
We do this with TLS (Transport Layer Security).

Very old LDAP clients used SSL, which had to be set up before the LDAP protocol
was started.
This has been deprecated for many years, and in fact SSL is now subject to several
known attacks so it should not be used.

TLS requires keys and certificates at the server end, and a trusted copy of
a signer certificate at the client end. The exact setup for this has not yet been
decided.

.. _locating-users:

.........................................
Locating the user entry
.........................................

LDAP identifies users using the full DN of their entry.
Humans will not want to remember or type such long strings of text, 
so the next job is to search for the user entry.
The user will have supplied a username and password, so the client application
must issue a search of the form:

base
    ou=people,dc=mozillians,dc=com

scope
    onelevel (preferred) or subtree

filter
    (uid=<username>)
    Where <username> is the username supplied by the end-user, encoded following the
    rules described in :ref:`handling-search-strings` below.

attributelist
    uid

If the username exists, the result should contain exactly one entry.
Because this search is usually done as the anonymous user, very little data
is returned in the entry - normally not even the *uid* value that was found by
the search.
The only information that we need from the search is the DN of the entry.

.........................................
Binding as the user
.........................................

If the search above returned exactly one entry, take it's DN and do
an LDAP simple bind using the DN and the password supplied by the end-user.
If the operation is successful then the user has supplied a valid username
and password, and the LDAP session is now bound as that user.

There is an important hazard to be aware of here, concerning passwords
and character sets.
See the :ref:`charset-hazards` section below for further details.

.........................................
Connection Management
.........................................

Once you have a connection open, it makes sense to use it for several operations
before closing it.

Connections can be re-bound as different users, but when doing this
it is important to re-bind as the anonymous user first to make sure that username
searches are not done using the permissions of some other user.

Avoid holding idle connections open for more than a minute or so.
Some network firewalls will silently drop the session data for idle TCP sessions,
leading to unexplained long delays when the client later tries to use them.

.........................................
Searching and reading data
.........................................

LDAP does not distinguish between search and read.
By default, search results are entries containing all 'user attributes' that
the requestor is allowed to see.
Note that this could be the empty set in some cases, and LDAP does not consider this to
be an error.

When looking for information about people, searches should be of the form:

base
    ou=people,dc=mozillians,dc=com

scope
    onelevel (preferred) or subtree

filter
    (&(objectclass=inetOrgPerson)(mozilliansVouchedBy=*)(<search criteria>))

    Where <search criteria> is built from the request made by the end-user.
    Search strings should be encoded following the
    rules described in :ref:`handling-search-strings` below except where
    explicit wildcards are required.

    Be aware that if you do not encode the search string then you are at risk
    of something like a SQL-injection attack, though in this case the damage
    is limited to returning unintended search results.

    Terms in search strings are combined using Polish notation, where the operator
    preceeds the operands. Each term must be enclosed in parentheses, and the whole
    search should also be enclosed in parentheses.

    The filter here uses (objectclass=inetOrgPerson) to make sure that we
    only get person entries, and (mozilliansVouchedBy=*) to limit the search
    to Mozillians and leave out un-vouched Applicants. Obviously if you want to
    see Applicants as well you can leave that bit out.

attributelist
    It is good practice to supply a list of the attributes that you actually
    have a use for.
    Bear in mind that the LDAP store may contain very large attributes such as
    photos and certificates: having these returned unnecessarily can slow the
    application and consume server resources.

Many searches are likely to return multiple entries. Others return none at all.
Neither case is considered an error in LDAP.

If a search matches a large number of entries, the LDAP server may apply an
administrative limit. In such cases the response will include some entries plus
a result code indicating that the limit was exceeded. Be aware that some LDAP
client libraries treat this as an error and discard the results.

In a future version of the project, there may be entries of various types stored
beneath the main *person* entry. These will provide specific information that expands
on the attributes found in the entry itself.

Similarly, future versions of the project are likely to have other branches
alongside the *ou=people* branch.

Entries contain *operational attributes* as well as *user attributes*.
These are not normally returned to the client unless explicitly requested.
Data obtainable from these attributes includes things like when the entry
was last modified, who did it, the full DN of the entry etc.
It is likely that we will restrict access to this data in a later release.

Some search forms are significantly slower than others.
This particularly affects expressions grouped with the logical-OR operator,
and those using non-indexed attributes.
Searches that yield very large potential result sets may be refused by the server.

These are 'good' search filters:

* (&(objectclass=inetOrgPerson)(uid=ab27))

  Good because the index on *uid* should instantly yield a single result

* (&(sn=smith)(mail=*@mozilla.com))

  Good because the *sn* index should yield a small result set that is then further
  reduced by checking the *mail* attribute.

These are 'bad' search filters:

* (cn=a*)

  Bad because it is likely to yield a very large result set.

* (\|(sn=smith)(favouriteDrink=dried leaves, boiled))

  Bad because favouriteDrink is not indexed, and due to the OR operator the *sn*
  attribute cannot help to cut down the search space.
  The LDAP server will have to examine every entry in the database.

.........................................
Modifying entries
.........................................

When bound to LDAP as a specific user it is possible to modify certain attributes
of that user's entry.
The exact list is defined in the access-control configuration of the server,
and currently includes:

* cn (MUST)
* displayName - a copy of the preferred cn value
* sn (MUST)
* uid (MUST because this is the username known to the user)
* mail
* telephoneNumber
* jpegPhoto
* description - this would hold the Bio

In addition the user can modify their own password: see below for details.

Users cannot change their own objectclass attributes, and any attempts to
completely remove any attribute labeled as MUST above will fail.
In other respects, standard LDAP practice applies.

LDAP does support language-specific values for most attributes,
but it is suggested that these should not be used for mozillians.org version 1.0.

.........................................
Changing passwords
.........................................

Users may change their own passwords.
To do this, bind as the user and then invoke the
*LDAP Password Modify Extended Operation* (RFC3062).
It is not currently necessary to supply the old password.

Some older LDAP clients change passwords by writing directly to the *userPassword*
attribute.
This is still supported, but it should be avoided for new code.

The *userPassword* attribute cannot be read by any normal user or administrator.
It is stored in a cryptographically-secure form using a one-way hash algorithm
to reduce the exposure if the server or backup media should be compromised.

.........................................
Creating new entries
.........................................

This can only be done by a special account belonging to the registration service.

It involves a normal LDAP ADD operation, but the entry must conform to certain rules:

#. The *objectclass* attribute must contain *inetOrgPerson* and *mozilliansPerson*
   but no other values (apart from the superclasses of those classes, which are optional)
#. *cn*, *sn*, and *uid* must have values
#. The value of *uid* must not clash with any existing entry
#. *uniqueIdentifier* must have a value, and it must not clash with any existing entry.
   The value used here should not expose any information about the user.
   A simple sequence counter may be appropriate.

.........................................
Vouching for new users
.........................................

When users first register at mozillians.org they are untrusted, and their
account has very little power above that granted to completely anonymous connections.
To become a full member of the community and gain the ability to search and read
data about other people, a new user must be 'vouched for' by an existing member.

To do this, the existing member finds the entry for the new user and writes
*their own DN* into the *mozilliansVouchedBy* attribute.
It is not possible to write any other value in this attribute, which preserves
accountability by showing who vouched for each member.

.. _charset-hazards:

---------------------------------------------------
Character-set hazards
---------------------------------------------------

Mozillians are a diverse bunch, from all over the world.
Not only will they have non-ASCII characters in their names and passwords,
but they will also have different default character sets in their various
computers.

This is not too much of a problem if each person always uses the
same computer (or at least, always uses one set up the same way) but it can
cause some very odd problems if they move around.
The biggest problem concerns the password, where LDAP does not specify the
character set to be used.
If a user sets 'pÅsswörd' as their password from a machine using UTF-8
they will be unable to login on a machine using ISO-8859-15 even though both
character sets include all the characters used:
the encoding is different and there is no way for the LDAP server to know
which encoding was used.

It may be possible to work around this by forcing all HTTP transactions
to use UTF-8, but any future applications that access LDAP directly will have
to be aware of the convention.

LDAP provides a recommendation in RFC4013, but implementation is optional
and is dependent on client developers to implement correctly.

.. _handling-search-strings:

---------------------------------------------------
Handling search strings
---------------------------------------------------

Certain characters have special meanings in LDAP search strings.
Examples include:

* '*' - used as a wildcard
* '(' and ')' - used to group expressiong
* '&', '|', '!' - used as operators

If any of these is to be included as literal text in a search string then it
must be escaped. 
Certain other characters and sequences must also be escaped in all cases
(these are mainly invalid UTF-8 encodings).

For full details, see RFC4515 section 3

