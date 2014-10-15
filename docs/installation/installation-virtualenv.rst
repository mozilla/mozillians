=======================
VirtualEnv Installation
=======================


.. note::

   Installing Mozillians might be daunting.  Ask for help using IRC in
   #commtools on irc.mozilla.org. Ping `giorgos`, `nemo-yiannis` or `tasos`,
   they will be happy to help.


**Prerequisites:** You'll need python 2.6, python-dev, virtualenv, pip,
a C compiler (for building some of the Python packages, like the DB interface),
mysqlclient and mysql-dev (or the equivalent on your system), a MySQL server, `gettext`_,
git, and lessc.  If you're working on translations, add subversion.

There are almost certainly other requirements that
we're so used to having installed we've forgotten we have them, so don't be shy
about asking on IRC for help if you run into unexpected errors.

You will want a \*nix box, ideally Debian or Ubuntu since that's what
most of the core developers are using and it's most likely to work.

If you're on Ubuntu or Debian, you might start with::

    $ sudo apt-get install build-essential git-core subversion \
    python2.6 python2.6-dev python-virtualenv python-pip \
    gettext libjpeg-turbo8-dev \
    mysql-client mysql-server libmysqlclient-dev

Then `install node <http://nodejs.org/>`_ and `lessc <http://lesscss.org/>`_.
(You only need node for lessc.)


.. note::

   Make sure your node version ``node -v`` is greater than v0.6.12 or there 
   will be issues installing less.


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

   .. note::

      Mac OS X users may see a problem when pip installs PIL. To correct that,
      install freetype, then do::

        sudo ln -s /opt/local/include/freetype2 /opt/local/include/freetype

      Once complete, re-run the pip install step to finish the installation.

#. Configure your local mozillians installation::

     (venv)$ cp mozillians/settings/local.py-devdist mozillians/settings/local.py

   The provided configuration uses a MySQL database named `mozillians` and
   accesses it locally using the user `mozillians`.  You can see
   :doc:`/installation/mysql` if you need help creating a user and database.

#. Download ElasticSearch::

     (venv)$ wget https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-1.2.4.tar.gz
     (venv)$ tar zxf elasticsearch-1.2.4.tar.gz

   and run::

     (venv)$ ./elasticsearch-1.2.4/bin/elasticsearch -d

  This will run the elasticsearch instance in the background.

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

   and start `elasticsearch` server again::

     (venv)$ ./elasticsearch-0.90.10/bin/elasticsearch

Have fun!

.. _gettext: http://playdoh.readthedocs.org/en/latest/userguide/l10n.html#requirements
.. _Fork the main Mozillians repository: https://github.com/mozilla/mozillians/fork
