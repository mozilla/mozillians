========================
BrowserID and Mozillians
========================

How the ...
-----------

BrowserID is implemented partially in Django, partially in our 
LDAP directory, and by using a new LDAP plugin `sasl-browserid`. 
This allows us to maintain the `LARPER security model`_.

.. _`LARPER security model`: ../apps/larper/__init__.py

.. image:: http://farm7.static.flickr.com/6067/6124318271_c7c0cee305_o.png
    :height: 356px
    :width: 600px
    :alt: Diagram of SASL BROWSER-ID plugin and Mozillians.org
    :target: http://www.flickr.com/photos/ozten/6124318271/

System Architecture
'''''''''''''''''''

Let's look at a typical authentication flow.

1. User clicks Sign-in button in HTML rendered from Django.

2. Browser requests an assertion from BrowserID.org.

3. Browser POSTs assertion to Django

4. Django code uses sasl_interactive_bind_s with BROWSER-ID as the auth mechanism. Assertion and audience are given as CB_USER and CB_AUTHNAME credentials.

5. SASL BROWSER-ID client plugin is loaded and sends a string:

  .. parsed-literal::

     assertion_value\\0audience_value\\0

6. SASL BROWSER-ID server plugin is loaded and parses inputs.

7. Server plugin uses `MySQL` queries based on the MD5 checksum of the assertion to see if the user already has an active session. It sees a cache miss.

8. Server plugin uses `Curl` to verify the assertion and audience with BrowserID.org.

9. Server plugin uses `YAJL` to parse the JSON response. It sees status set to "okay". It sees an email address.

10. Server plugin creates a session which contains a MD5 digest of the assertion, the user's email address, and the current timestamp.

11. Server plugin sets authid and authname to the user's email address.

12. `slapd` attempts to map the username into a valid DN. It uses the following configuration:

  .. parsed-literal::

      authz-regexp
        uid=([^,]*),cn=browser-id,cn=auth
        ldap:///ou=people,dc=mozillians,dc=org??one?(uid=$1)

Example: `slapd` has `dn:uid=shout@ozten.com,cn=browser-id,cn=auth` as the user's DN. It searches for uid=shout@ozten.com which matches one record. `slapd` then set's the user's identity to `uniqueIdentifier=32aef32b,dc=mozillians,dc=org`.

13. Server plugin returns a success status to the client.

14. Client returns a success status to Django.

15. Django uses `ldap_whoami_s` to determine the DN of the current user.

16. The DN *does not* contain `,cn=browser-id,cn=auth`, so Django treats this as a successful BrowserID login.

17. The `assertion` is stored securly in Django's session (via a signed cookie).

BrowserID Session
'''''''''''''''''''
We authenticate the user via BrowserID which gives us an email address.
This will either be a valid email address in the system or will be
an unknown email address. We maintain a 6 hour session during which
we do not re-authenticate the user. This session is managed outside
of Django via a crontab. The crontab lives under bin/crontab/ for 
developer convience, but in stage and production is a seperate component.

Development Mode:

    bin/crontab/session_cleaner.py --django

Production Mode:

    bin/crontab/session_cleaner.py

In production mode, the cron will read from session_cleaner_conf.py

The session table contains only a MD5 digest of assertions, email addresses, and timestamps.

The table *should not* be accessible to middleware and is only accessed from the Server side plugin, running on the slapd machines.

Current Session Flow
''''''''''''''''''''
Let's examine a similar flow, but for a user with a current session.

1. Browser sends session Cookie.

2. Django decrypts assertion and uses it with the audience in a sasl_interactive_bind_s. Steps 4 through 6 of original flow.

3. Server plugin checks for an active session using an MD5 digest of the assertion. It finds a session cache hit and retrieves the email address.

4. Server plugin updates the timestamp of this session.

5. Steps 11 through 17 happen just like our original flow, with the Server plugin setting the authid and authname to the user's email address.

Stale Session Flow
''''''''''''''''''''
This time our user's BrowserID Session has timedout.

1. Browser sends session Cookie.

2. Django decrypts assertion and uses it with the audience in a sasl_interactive_bind_s. Steps 4 through 6 of original flow.

3. Server plugin checks for an active session using an MD5 digest of the assertion. It sees a cache miss (Identical to step 7 in original flow).

4. Server plugin goes through steps 8 and 9, but this time the JSON response contains status set to "failure". This is because the assertion and audience inputs are no longer valid.

5. Server plugin returns a auth failure code.

6. Client returns an auth failure code.

7. Django code checks for failure. It clears the current session.

New User Flow
'''''''''''''

Considering our original flow, if at step 16 the DN *did* contain `,cn=browser-id,cn=auth`, the we would have a new user. The following captures that flow.

1. The email address is parsed out from the DN.

2. For compatiblity with django-auth-ldap as well as maintaining user analytics, basic information about the user are recorded in the Django MySQL database.

3. The user is logged in. The user's assertion is set into the Django session.

4. The email address is noted in the session as a new user. The user is sent to the registration path to complete their creation of a LDAP user account.

Libraries
'''''''''
We reuse the JS and Form from `django-browserid`_, but the backend and other 
bits don't match our requirements.

We use the `SASL BROWSER-ID`_ authentication mechanism via a plugin running
under OpenLDAP.

The remaining glue is provided by apps/browserid.

.. _`django-browserid`: https://github.com/mozilla/django-browserid
.. _`SASL BROWSER-ID`: https://github.com/ozten/sasl-browserid


UX and Flow
-----------
Login or Registration flows now begin on the homepage. There is no
/login url. @login_required decorators have been upgraded to redirect
the user to /.

At the homepage, the user clicks either 'Log In' or 'Join Us'. Both 
launch the BrowserID flow which gets a verified email. Which link 
is noted, to help message the user in corner cases.

Once we have an assertion, we store it in the session and then we attempt 
to authenticate the user via a BrowserID enabled LDAP backend. 

Unknown Email
'''''''''''''
If the user isn't known, then they are redirected to /register. 
There they will enter profile information and create their account.
If the user originally clicked 'Log In', a warning will be shown with
the chance to choose another email address.

Existing Email
''''''''''''''
The user is logged in.

Django Session
'''''''''
Assertions must be retained during a session, since they are used to connect to LDAP.
In 1.0 we used signed_cookies as the Django session backend. This allowed us to 
store the clear text password. We could replace password with assertion, except that
assertions can be up to 4,000 characters long. We will switch the backend to Django's
standard database backed sessions. Benefits, a small session ID can be used to "lookup" the 
full assertion. The assertions will be signed to make it harder to get all assertions from the database..

SESSION_ENGINE = "django.contrib.sessions.backends.db"
After a couple days (effectively next release) do
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

Reason - signed_cookies has been storing a big blob under 'sessionid'. Session engine tries to decode that into key value pairs and hits a
MemcachedKeyLengthError at /
Key length is > 250

By moving to db before cached_db we avoid this technical issues.

Alternative - Have IT delete all session data - we can't they are in cookies.


Passwords
'''''''''
All logic and templates to support a password based authenticatio have
been removed. New user accounts are marked as having unusable passwords.

Debugging
'''''''''

Once slapd has successfully authenticated an assertion/audience pair, then 
it is in the browserid_session cache. This is quite useful for debugging.

I usually set an environment variable A to an assertion value.

    A=eyJjZXJ0aWZpY2F0ZXMiOls...some_long_string...S0R1a1Z1QlBkUkpHZkF6VUJ3In0

Then you can issue commands to debug the system as that user:

    ldapwhoami -Y BROWSER-ID -H ldap://:1389/  -X $A -U 'http://localhost:8001'

    ldapsearch -Y BROWSER-ID -H ldap://:1389/ -b 'dc=mozillians,dc=org' "(&(objectClass=mozilliansPerson)(mail=*ozten*))" -X $A -U 'http://localhost:8001'

Problem:
using ldapwhoami I always get
dn:uid=foo@example.com,cn=browser-id,cn=auth
I've checked and uid=foo@example.com exists, what gives?

Solution:
Are you missing authz-regexp config in slapd.conf or is it incorrect?

Problem:
Login hangs for a long time and then the homepage reloads.

Solution:
Your vagrant VM isn't able to reach the internet.
If you tail /var/log/auth.log you might see

    Dec  6 17:10:06 lucid32 browserid-server: curl_easy_perform failed [6] Couldn't resolve host name
    Dec  6 17:10:06 lucid32 browserid-server: No dice, STATUS=[curl-error] REASON=[Couldn't resolve host name]
    Dec  6 17:10:06 lucid32 browserid-server: SASL [conn=1032] Failure: Couldn't resolve host name
    Dec  6 17:10:06 lucid32 browserid-server: conn=1032 op=0 RESULT tag=97 err=49 text=SASL(-13): authentication failure: Couldn't resolve host name

Another test is 

    curl https://browserid.org/

To fix:

    sudo /etc/init.d/networking restart



Unit Tests
''''''''''

The Vagrant VM is setup to allow for development and unit tests.

LDAP has it's own MySQL database with the following data pre-populated:

INSERT INTO browserid_session(digest, email) VALUES (MD5('abcdefghijklmnop'), 'u000001@mozillians.org');
INSERT INTO browserid_session(digest, email) VALUES (MD5('qrstuvwxyz'), 'u000003@mozillians.org');
INSERT INTO browserid_session(digest, email) VALUES (MD5('newabcdefghi'), 'new@test.net');
INSERT INTO browserid_session(digest, email) VALUES (MD5('somelongstring'), 'u000098@mozillians.org');
INSERT INTO browserid_session(digest, email) VALUES (MD5('mrfusionsomereallylongstring'), 'mr.fusion@gmail.com');
INSERT INTO browserid_session(digest, email) VALUES (MD5('mr2reallylongstring'), 'mr2@gmail.com');


