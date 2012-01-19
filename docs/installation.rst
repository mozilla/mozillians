.. _installation:

============
Installation
============

.. note::
    Installing Mozillians might be daunting.  Ask for help in #mozillians on
    irc.mozilla.org.  tofumatt, ednapiranha or davedash will be happy to help.

You'll need ruby, vagrant, Virtualbox and git.  The following steps will help you:


1. Install vagrant (requires ``ruby``)::

    $ gem install vagrant

   .. seealso::
      `Vagrant: Getting Started
       <http://vagrantup.com/docs/getting-started/index.html>`_

2. Install virtualbox_ by Oracle.

   .. note::
      If you run Linux, you'll need to make sure virtualization isn't disabled
      in your kernel.

.. _virtualbox: http://www.virtualbox.org/


3. Get a copy of Mozillians.org::

    $ git clone --recursive git://github.com/mozilla/mozillians.git mozillians
    $ cd mozillians


4. Run a virtual dev environment::

    $ vagrant up
    $ vagrant ssh # you will now enter the virtualized environment

   .. note:: Run this in your working copy directory (i.e. ``mozillians/``)

   You can edit files under (``mozillians/``) locally and they will automatically
   show up under /home/vagrant/mozillians in the virtualbox.  This means you can edit
   in your favorite text-editor, yet run Mozillians from our virtualized environment.

6. Setup the databases::

    $ ./manage.py syncdb
    $ ./manage.py migrate

6. Run the development web server (in the virtualized environment)::

    $ ./manage.py runserver 0.0.0.0:8001

7. Point your web browser to http://localhost:8001

   .. note::
      If you don't want to use 8001, edit the Vagrant script which
      maps your virtualbox port. Then restart vagrant::

          vargrant halt && vagrant up

8. Stay up to date

   On your host machine do::

    $ git pull -q origin master
    $ git submodule update --recursive
    $ pushd vendor
    $ git pull -q origin master
    $ git submodule update --recursive
    $ popd
    $ vagrant destroy && vagrant up
$
   Within your vagrant VM do::

    dj syncdb
    dj manage
