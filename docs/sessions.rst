=============
LDAP Sessions
=============

Access to the LDAP directory is done by logging into an LDAP server as the
end-user.  This is different
from a database which traditionally has the same privileged account regardless
of who the end user is.

For example:

===== =================== ====================
User  LDAP directory user Mysql Database user
===== =================== ====================
Sally sally@draper.com    mozillians@localhost
Gene  gene@draper.com     mozillians@localhost
Don   don@draper.com      mozillians@localhost
Bobby bobby@draper.com    mozillians@localhost
Betty betty@draper.com    mozillians@localhost
===== =================== ====================

This means we need to somehow store the users credentials each time they log
in.

.. note::
    This may change down the road if we implement different LDAP
    authentication layers.

We do this by writing the password to an encrypted cookie in a post-login
signal.

This takes advantage of the Django's
:ref:`cookie based session backend<django:cookie-session-backend>` and
the new :py:mod:`django.core.signing`.

