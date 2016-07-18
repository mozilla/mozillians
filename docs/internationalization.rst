Internationalization
====================

How to help with internationalization of Mozillians.org.

Installation
------------

The message files used for translation are not in the same repository as
the code, so if you are going to work on internationalization of
Mozillians, you'll need to do a little more installation work.

#. Install `git` client

#. Clone the messages files repository under `locale` like this::

      git clone https://github.com/mozilla-l10n/mozillians-l10n.git locale

   .. note::

      The directory in the git repository is named ``locales`` but it has to
      be checked out to a local directory named ``locale``.

Working on internationalization
-------------------------------
Having checked out the message files, you should be able to use the following
instructions for Mozillians.org internationalization.

* For strings in python code we are using
  `django's l10n functionality <https://docs.djangoproject.com/en/1.8/topics/i18n/translation/#standard-translation>`_.
* For strings in jinja2 templates we are using `Puente <https://puente.readthedocs.io/>`_.


Managing Strings
----------------

.. note::

   This section is for mozillians.org core developers. Other
   Mozillians *do not* have to do any of the following to contribute
   to mozillians.org.


.. _update-pontoon:

Update Pontoon
^^^^^^^^^^^^^^

When we commit new strings or we alter already existing strings in our
codebase we need to perform a string merge to update Pontoon.
`Pontoon <https://pontoon.mozilla.org/projects/mozillians/>`_ is the
tool localizers use to translate mozillians.org strings.

Steps to follow to perform a string merge:

  #. Update your local git repository::

       cd locale
       git checkout master
       git pull origin master

  #. String extract and merge::

       ./manage.py extract
       ./manage.py merge

  #. Check the diff to make sure things look normal::

       cd locale
       git status
       git diff

     .. note::

        Make sure things look normal. Changes in libraries
        (e.g. tower) can break things, like remove half of the
        strings.

  #. Lint translations. See :ref:`linting-translations`.

  #. Commit to git repository::

       git commit -a -m "Mozillians string merge"

  #. Push changes to *master* branch::

       git push origin master

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
the *production* branch instead of *master*.

   #. Make sure that the translations in *master* have no errors. See :ref:`linting-translations`

      .. warning::

         Translations with errors can bring (pages of the) website
         down. The template engine will fail to parse the strings and
         a 500 error will be returned to users. It is really important
         that translations copied to production are correct.

   #. Checkout production branch if you don't have it already::

        cd locale
        git fetch origin
        git checkout production

   #. Merge current *master* into *production*::

        git merge master

   #. Verify that everything looks good::

        git status
        git diff

   #. Commit merge to production branch::

        git commit -a -m "Update mozillians production strings."

   #. Push new strings to production branch::

        git push origin production

   #. Production will get the new translations on next push.
