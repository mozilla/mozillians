=======================
VirtualEnv Installation
=======================


.. note::

   Installing Mozillians might be daunting.  Ask for help in
   #commtools on irc.mozilla.org. Ping `giorgos`, `sancus` or `hoosteeno`, 
   they will be happy to help.


**Prerequisites:** You 'll need python 2.6, virtualenv and pip.  You'll also need
mysql-dev (or the equivalent on your system), and MySQL server.

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

     $ virtualenv --no-site-packages venv

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

#. Download and run elastic search::

     (venv)$ wget http://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-0.20.0.tar.gz -O /tmp/es.tar.gz
     (venv)$ tar xvf /tmp/es.tar.gz -C $VIRTUAL_ENV
     (venv)$ $VIRTUAL_ENV/elasticsearch-0.20.0/bin/elasticsearch -p $VIRTUAL_ENV/es.pid

   That will start elastic search in the background; be sure to see the instructions
   later on for stopping it when you're done working on Mozillians.

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

   When you are done with your coding session, do not forget to kill the `elastic
   search` process::

     (venv)$ kill `cat $VIRTUAL_ENV/es.pid`

   and deactivate your virtual python environment by running::

     (venv)$ deactivate
     $

#. Next time:

   Next time, before starting you will need to activate your environment by typing::

     $ . $VIRTUAL_ENV/bin/activate

   and start the `elasticsearch` server again::

     $ $VIRTUAL_ENV/elasticsearch-0.19.4/bin/elasticsearch -p $VIRTUAL_ENV/es.pid

Have fun!

.. _Fork the main Mozillians repository: https://github.com/mozilla/mozillians/fork_select
