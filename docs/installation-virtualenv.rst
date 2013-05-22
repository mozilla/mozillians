=======================
VirtualEnv Installation
=======================


.. note::

   Installing Mozillians might be daunting.  Ask for help in
   #commtools on irc.mozilla.org. Ping `giorgos`, he will be happy to
   help.


**Prerequisites:** You 'll need python, virtualenv and pip.

When you want to start contributing...

#.  `Fork the main Mozillians repository`_ (https://github.com/mozilla/mozillians) on GitHub.

#.  Clone your fork to your local machine::

    $ git clone --recursive git@github.com:YOUR_USERNAME/mozillians.git mozillians
    $ cd mozillians

    .. note::

       Make sure you use ``--recursive`` when checking the repo out! If you
       didn't, you can load all the submodules with ``git submodule update --init
       --recursive``.

#. Create your python virtual environment::

     $ virtualenv --no-site-packages venv

#. Activate your python virtual environment::

     $ source venv/bin/activate

#. Install development and compiled requirements::

     (venv)$ pip install -r requirements/compiled.txt -r requirements/dev.txt

   .. note::

      When you activate your python virtual environment 'venv'
      (virtual environment's root directory name) will be prepended
      to your PS1.


   .. note::

      Since you are using a virtual environment all the python
      packages you will install while the environment is active,
      will be available only within this environment. Your system's
      python libraries will remain intact.

#. Configure your local mozillians installation::

     (venv)$ cp settings/local.py-devdist settings/local.py

   .. note::

      The provided configuration uses a sqlite database with the
      filename `mozillians.db` and assumes that server listens to
      `127.0.0.1:8000`. You can alter the configuration to fit your
      own needs.

#. Download and run elastic search::

     (venv)$ wget http://download.elasticsearch.org/elasticsearch/elasticsearch/elasticsearch-0.19.4.tar.gz -O /tmp/es.tar.gz
     (venv)$ tar xvf /tmp/es.tar.gz -C venv/
     (venv)$ ./venv/elasticsearch-0.19.4/bin/elasticsearch -p venv/es.pid >/dev/null 2>&1

#. Update product details::

     (venv)$ ./manage.py update_product_details -f

#. Sync DB::

     (venv)$ ./manage.py syncdb --noinput && ./manage.py migrate

#. Create user:

     #. Run server::

        ./manage.py runserver 127.0.0.1:8000

     #. Load http://127.0.0.1:8000 and sign in with BrowserID, then create your profile.
     #. Automatically vouch your account and convert it to superuser::

        ./scripts/su.sh


#. Develop!

   Now you can start :doc:`contributing to Mozillians </contribute>`. When you are
   done with your coding session, do not forget to kill the `elastic
   search` process::

     (venv)$ kill `cat venv/es.pid`

   and deactivate your virtual python environment by running::

     (venv)$ deactivate

   Next time, before starting you will need to start `elasticsearch`
   server again::

     $ ./venv/elasticsearch-0.19.4/bin/elasticsearch -p venv/es.pid >/dev/null 2>&1

   and activate your environment by typing::

     $ source venv/bin/activate

   Have fun!

.. _Fork the main Mozillians repository: https://github.com/mozilla/mozillians/fork_select
