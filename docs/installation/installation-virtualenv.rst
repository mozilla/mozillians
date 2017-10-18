=======================
VirtualEnv Installation
=======================


.. note::

   Installing Mozillians might be daunting.  Ask for help using IRC in
   #commtools on irc.mozilla.org. Ping `giorgos`, `nemo-yiannis` or `tasos`,
   they will be happy to help.

************
Dependencies
************

**Prerequisites:** You'll need python2.7, python2.7-dev, virtualenv, pip,
a C compiler (for building some of the Python packages, like the DB interface),
mysqlclient and mysql-dev (or the equivalent on your system), a MySQL server, `gettext`_,
git, and lessc. Also, since we use elasticsearch, you will need a JAVA runtime environment.

There are almost certainly other requirements that
we're so used to having installed we've forgotten we have them, so don't be shy
about asking on IRC for help if you run into unexpected errors.

You will want a \*nix box, ideally the latest versions of Debian or Ubuntu
since that's what most of the core developers are using and it's most likely
to work.

If you're on Ubuntu or Debian, you might start with::

    $ sudo apt-get install build-essential git-core \
    python2.7 python2.7-dev python-virtualenv python-pip \
    gettext libjpeg-turbo8-dev \
    mysql-client mysql-server libmysqlclient-dev default-jre \
    libxslt2.1 libxslt1-dev libjpeg-dev zlib1g-dev libpng12-dev

Then `install node <http://nodejs.org/>`_ and `lessc <http://lesscss.org/#using-less-installation>`_ (you only need node for ``lessc``).

``nodejs`` is not packaged for every distribution so we will not get into details
as that would require different instructions for every distribution.
You might want to take a look at `nodejs github wiki <https://github.com/joyent/node/wiki/installing-node.js-via-package-manager>`_.
Just bare in mind that ``lessc`` must be installed after ``nodejs``, since you have
to use ``npm``, the package manager of ``nodejs``.


.. note::

   Make sure your node version ``node -v`` is greater than v0.6.12 or there
   will be issues installing less.


When you want to start contributing...

#.  `Fork the main Mozillians repository`_ (https://github.com/mozilla/mozillians) on GitHub.

#.  Clone your fork to your local machine::

       $ git clone git@github.com:YOUR_USERNAME/mozillians.git mozillians
       (lots of output - be patient...)
       $ cd mozillians

#. Create your python virtual environment::

     $ virtualenv venv

#. Activate your python virtual environment::

     $ source venv/bin/activate
     (venv) $

   .. note::

      When you activate your python virtual environment, 'venv'
      (virtual environment's root directory name) will be prepended
      to your PS1.

#. Install development requirements::

     (venv)$ python ./scripts/pipstrap.py
     (venv)$ pip install --require-hashes --no-deps -r requirements/dev.txt
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

     (venv)$ cp mozillians/env-dist mozillians/.env

   The provided configuration uses a MySQL database named `mozillians` and
   accesses it locally using the user `mozillians`.

#. Download ElasticSearch::

     (venv)$ wget https://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-2.4.5.tar.gz
     (venv)$ tar zxf elasticsearch-2.4.5.tar.gz

   and run::

     (venv)$ ./elasticsearch-2.4.5/bin/elasticsearch -d

  This will run the elasticsearch instance in the background.


***********
MySQL setup
***********

Setting up a MySQL user and database for development:

#. Install the MySQL server. Many Linux distributions provide an installable
   package. If your OS does not, you can find downloadable install packages
   on the `MySQL site`_.

#. Start the mysql client program as the mysql root user::

    $ mysql -u root -p
    Enter password: ........
    mysql>

#. Create a ``mozillians`` user::

    mysql> create user 'mozillians'@'localhost';

#. Create a ``mozillians`` database::

    mysql> create database mozillians character set utf8;

#. Give the mozillians user access to the mozillians database::

    mysql> GRANT ALL PRIVILEGES ON mozillians.* TO "mozillians"@"localhost";
    mysql> EXIT
    Bye
    $

#. Install timezone info tables in mysql::

   (venv)$ mysql_tzinfo_to_sql /usr/share/zoneinfo/ | mysql -uroot -p mysql

.. _MySQL site: http://dev.mysql.com/downloads/mysql/


******************
Running Mozillians
******************

#. Update product details::

     (venv)$ ./manage.py update_product_details -f

#. Apply migrations::

     (venv)$ ./manage.py migrate

#. Create user:

     #. Run server::

        ./manage.py runserver 127.0.0.1:8000

     #. Load http://127.0.0.1:8000 and sign in with Persona, then create your profile.
     #. Stop the server with ``Ctrl^C``.
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

     (venv)$ ./elasticsearch-2.4.5/bin/elasticsearch -d

Have fun!

.. _gettext: http://playdoh.readthedocs.org/en/latest/userguide/l10n.html#requirements
.. _Fork the main Mozillians repository: https://github.com/mozilla/mozillians/fork
