Translation
===========

How to help with internationalization of Mozillians.org.

Installation
------------

The message files used for translation are not in the same repository as
the code, so if you are going to work on internationalization of
Mozillians, you'll need to do a little more installation work.

#. Install a subversion client

#. Check out the messages files under `locale` like this::

      mkdir locale
      svn co http://svn.mozilla.org/projects/l10n-misc/trunk/mozillians/locales locale

   .. note::

      The directory in subversion is named ``locales`` but it has to be checked
      out to a local directory named ``locale``.

Working on internationalization
-------------------------------

Having checked out the message files, you should be able to use the
`instructions from Playdoh <http://playdoh.readthedocs.org/en/latest/userguide/l10n.html>`_
for Mozillians.org as well.
