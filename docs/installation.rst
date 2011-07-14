.. _installation:

============
Installation
============


1. Install vagrant::

    gem install vagrant

2. Install virtualbox_ by Oracle.

.. _virtualbox: http://www.virtualbox.org/

2. Get a copy of Mozillians.org::

    git clone --recursive git://github.com/mozilla/mozillians.git mozillians.org

3. Run a virual dev environment::

    vagrant up
    vagrant ssh

   You can edit your files locally and they will automatically
   show up under /vagrant in the virtualbox.

4. Start your engines::

    vagrant@lucid32$ cd /vagrant/directory/localtest
    vagrant@lucid32:/vagrant/directory/localtest$ x-rebuild
    vagrant@lucid32:/vagrant/directory/localtest$ cd ../..
    vagrant@lucid32:/vagrant/$ ./manage.py runserver 0.0.0.0:8001

5. Point your browser to http://localhost:8001

   If you don't want to use 8001, edit the Vagrant script which
   maps your virtualbox port. Then restart vagrant::

    vargrant halt && vagrant up

6. Optional - Install a directory viewer (Apache Directory Studio)

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

7. Stay up to date

   On your local desktop do::

    ./bin/update_site -e dev -v
    vagrant destroy && vagrant up
