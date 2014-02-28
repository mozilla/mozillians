=======================
VirtualEnv Installation
=======================


.. note::

   Installing Mozillians might be daunting.  Ask for help in
   #commtools on irc.mozilla.org. Ping `giorgos`, `sancus` or `hoosteeno`,
   they will be happy to help.


**Prerequisites:** You'll need python 2.6, virtualenv and pip.  You'll also need
mysql-dev (or the equivalent on your system), a MySQL server and `gettext`_.

You will probably also want a \*nix box; Mozillians.org is tricky to install on Windows.

When you want to start contributing...

#.  `Fork the main Mozillians repository`_ (https://github.com/mozilla/mozillians) on GitHub.

#.  Clone your fork to your local machine::

       $ git clone --recursive git@github.com:YOUR_USERNAME/mozillians.git mozillians
       (lots of output - be patient...)
       $ cd mozillians

    .. note::

       Make sure you use ``--recursive`` when checking the repo out! If you
       didn't, you can load all the submodules with ``git submodule update --init
       --recursive``.

#. Create your python virtual environment::

     $ virtualenv venv

#. Activate your python virtual environment::

     $ source venv/bin/activate
     (venv) $

   .. note::

      When you activate your python virtual environment, 'venv'
      (virtual environment's root directory name) will be prepended
      to your PS1.

#. Install development and compiled requirements::

     (venv)$ pip install -r requirements/compiled.txt -r requirements/dev.txt
     (lots more output - be patient again...)
     (venv) $

   .. note::

      Since you are using a virtual environment, all the python
      packages you will install while the environment is active
      will be available only within this environment. Your system's
      python libraries will remain intact.

#. Configure your local mozillians installation::

     (venv)$ cp mozillians/settings/local.py-devdist mozillians/settings/local.py

   The provided configuration uses a MySQL database named `mozillians` and
   accesses it locally using the user `mozillians`.  You can see
   :doc:`mysql` if you need help creating a user and database.

#. Download from http://www.elasticsearch.org/download decompress and
   run elastic search.


#. Update product details::

     (venv)$ ./manage.py update_product_details -f

#. Sync DB and apply migrations::

     (venv)$ ./manage.py syncdb --noinput --migrate

#. Create user:

     #. Run server::

        ./manage.py runserver 127.0.0.1:8000

     #. Load http://127.0.0.1:8000 and sign in with Persona, then create your profile.
     #. Vouch your account and convert it to superuser::

        ./scripts/su.sh

#. Develop!

   Now you can start :doc:`contributing to Mozillians </contribute>`.

#. When you're done:

   When you are done with your coding session, do not forget to kill
   the `elasticsearch` process and deactivate your virtual python
   environment by running::

     (venv)$ deactivate
     $

#. Next time:

   Next time, before starting you will need to activate your environment by typing::

     $ . $VIRTUAL_ENV/bin/activate

   and start the `elasticsearch` server again.

Have fun!

.. _gettext: http://playdoh.readthedocs.org/en/latest/userguide/l10n.html#requirements
.. _Fork the main Mozillians repository: https://github.com/mozilla/mozillians/fork
