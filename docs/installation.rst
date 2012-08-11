.. _installation:

============
Installation
============

.. note::
    Installing Mozillians might be daunting.  Ask for help in #mozillians on
    irc.mozilla.org.  tofumatt, timw, or tallOwen will be happy to help.

You'll need ruby, vagrant, Virtualbox and git.  The following steps will help
you:


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

5. Setup the database::

    $ ./manage.py syncdb --noinput
    $ ./manage.py migrate

    .. note::
    Some people have run into issues with existing south migrations that
    have note run. To remedy this run ``mysql -u root`` to get into the mysql
    shell. From there run ``drop database mozillians;`` and ``create database mozillians;``
    and quit with ``\q``. Run the ``syncdb`` and ``migrate`` commands as above again.

6. Run the development web server (in the virtualized environment)::

    $ ./manage.py runserver 0.0.0.0:8000

  .. note::
      ``rs`` is one of the many handy Django aliases included in the
      Mozillians VM. It's aliases to ``./manage.py runserver 0.0.0.0:8000``. You
      can see all the aliases available by typing ``alias`` inside your VM shell
      or by inspecting the contents of ``puppet/files/home/vagrant/zshrc`` (or
      ``bashrc_vagrant`` if you use ``bash``).

7. Point your web browser to http://localhost:8000

8. Stay up-to-date::

   On your host machine do::

    $ git pull -q origin master
    $ git submodule update --recursive
    $ pushd vendor
    $ git pull -q origin master
    $ git submodule update --recursive
    $ popd

   Then you can run any needed database migrations inside your VM::

    $ dj syncdb
    $ dj migrate

   Occassionally there will be a new base VM box. If so, get it with::

    $ vagrant destroy
    $ vagrant up
