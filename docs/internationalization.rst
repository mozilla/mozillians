Internationalization
====================

How to help with internationalization of Mozillians.org.

Installation
------------

The message files used for translation are not in the same repository as
the code, so if you are going to work on internationalization of
Mozillians, you'll need to do a little more installation work.

#. Install a subversion client

#. Check out the messages files under `locale` like this::

      svn co http://svn.mozilla.org/projects/l10n-misc/trunk/mozillians/locales locale

   .. note::

      The directory in subversion is named ``locales`` but it has to be checked
      out to a local directory named ``locale``.

   .. note::

      If you plan to commit string merges make sure that you use the https URL::

        svn co https://svn.mozilla.org/projects/l10n-misc/trunk/mozillians/locales locale

Working on internationalization
-------------------------------

Having checked out the message files, you should be able to use the
`instructions from Playdoh <http://playdoh.readthedocs.org/en/latest/userguide/l10n.html>`_
for Mozillians.org as well.


Managing Strings
----------------

.. note::

   This section is for mozillians.org core developers. Other
   Mozillians *do not* have to do any of the following to contribute
   to mozillians.org.


.. _update-verbatim:

Update Verbatim
^^^^^^^^^^^^^^^^^

When we commit new strings or we alter already existing strings in our
codebase we need to perform a string merge to update
Verbatim. `Verbatim
<https://localize.mozilla.org/projects/mozillians>`_ is the
tool localizers use to translate mozillians.org strings.

Steps to follow to perform a string merge:

  #. Inform `mathjazz <https://mozillians.org/en-US/u/mathjazz/>`_ on
     IRC in channel `#l10n` that you're about to do a string merge. If
     mathjazz is not available try to find `pascalc
     <https://mozillians.org/en-US/u/pascalc/>`_.

     .. warning::

        Before updating SVN with new strings we need to make sure that
        the changes made in Verbatim are committed to SVN. The #l10n
        team will take care of that. It's important that we ping them
        *before* we commit anything to SVN.

     When you get the green light from #l10n move to step 2.

  #. Update your local svn repository::

       cd locale
       svn up

  #. String extract and merge::

       ./manage.py extract -c
       ./manage.py merge -c

  #. Check the diff to make sure things look normal::

       cd locale
       svn diff

     .. note::

        Make sure things look normal. Changes in libraries
        (e.g. tower) can break things, like remove half of the
        strings.

  #. Lint translations. See :ref:`linting-translations`.

  #. Commit to SVN::

       svn ci -m "Mozillians string merge"

  #. Inform #l10n what you committed new changes and they will update
     Verbatim.

  #. Optionally update production. See :ref:`updating-production-translations`.


.. _linting-translations:

Linting translations
^^^^^^^^^^^^^^^^^^^^

Sometimes translations have coding errors. Fortunately there is tool
called `dennis <https://github.com/willkg/dennis>`_ which will find
all the errors.

  #. Make sure you have dennis::

       pip install dennis

  #. Run dennis linter::

       dennis-cmd lint locale

  #. If dennis returns no errors or warnings your job is
     done. Otherwise continue reading.

  #. Visit each file that dennis reports and locate the problematic translation:

       a. Sometimes translations with variables are missing special
          characters. This can be easily fixed and you can do
          it. Here's an example:

          Here is the original, English string::

            msgid "Sorry, we cannot find any mozillians with skill %(name)s"

          and a incomplete Spanish translation::

            msgstr "Discúlpanos, pero no encontramos ningún mozillero en %(name)"

          The Spanish translation is missing a final `s` right after
          `%(name)`. The missing character is part of the variable
          definition and without it the template engine cannot parse
          the template.

          We fix the incomplete translation by adding the missing
          character.

       #. If the translation needs attention from the translator we
          add `fuzzy` flag to the translation. This way we don't
          delete the broken translation but we instruct the template
          engine not to use it.

          For example for this translation::

            #: mozillians/templates/groups/skill.html:31
            msgid "Sorry, we cannot find any mozillians with skill %(name)s"
            msgstr "Something is wrong here"

          we add a line like this::

            #: mozillians/templates/groups/skill.html:31
            #, fuzzy
            msgid "Sorry, we cannot find any mozillians with skill %(name)s"
            msgstr "Something is wrong here"


.. _updating-production-translations:

Updating Production Translations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Production server https://mozillians.org checks out translations from
the *production* tag instead of trunk.

   #. Make sure that the translations in *trunk* have no errors. See :ref:`linting-translations`

      .. warning::

         Translations with errors can bring (pages of the) website
         down. The template engine will fail to parse the strings and
         a 500 error will be returned to users. It is really important
         that translations copied to production are correct.

   #. Checkout production repository if you don't have it already::

        svn co https://svn.mozilla.org/projects/l10n-misc/tags/production/mozillians/locales

   #. Merge current *trunk* into *production*::

        svn merge https://svn.mozilla.org/projects/l10n-misc/trunk/mozillians/locales

   #. Verify that everything looks good::

        svn diff
        svn status
        svn info

   #. Commit merge to production tag::

        svn ci -m "Update mozillians production strings."

   #. Production will get the new translations on next push.
