.. _installation:

============
Installation
============


1. Install vagrant::

    gem install vagrant

2. Install virtualbox_ by Oracle.

.. _virtualbox: http://www.virtualbox.org/

3. Get a copy of Mozillians.org::

    git clone --recursive git://github.com/mozilla/mozillians.git mozillians.org

4. Get a copy of Mozillians.org's LDAP backend::

    pushd mozillians.org
    git clone git://github.com/mozilla/mozillians-ldap.git directory
    popd

5. Run a virual dev environment::

    vagrant up
    vagrant ssh

   You can edit your files locally and they will automatically
   show up under /home/vagrant/mozillians in the virtualbox.

6. Start your engines::

    $ pushd mozillians/directory/devslapd && x-rebuild && popd
    $ cd mozillians
    $ ./manage.py runserver 0.0.0.0:8001

7. Point your browser to http://localhost:8001

   If you don't want to use 8001, edit the Vagrant script which
   maps your virtualbox port. Then restart vagrant::

    vargrant halt && vagrant up

8. Optional - Install a directory viewer (Apache Directory Studio)

   Visit http://directory.apache.org/studio/download/download-linux.html and
   download the (100MB!) Apache Directory Studio.
   Unzip the tarball and run the file (requires Java).

   a. Click "go to the workbench".
   b. Click "New Connection" in the Connections window in the bottom left
   c. Name: Mozillians Vagrant Director
   d. Hostname: localhost
   e. Port: 1389
   f. <Next>
   g. Bind DN or user: cn=root,dc=mozillians,dc=org
   h. Bind password: secret
   i. Click "Finish"
   j. Double-click on the resulting connection and you should see the test data.

   The refresh button is F5.

9. Stay up to date

   On your local desktop do::

    git pull -q origin master
    git submodule update --recursive
    pushd vendor
    git pull -q origin master
    git submodule update --recursive
    popd
    vagrant destroy && vagrant up

   With you vagrant VM do::

    python vendor/src/schematic/schematic migrations/
