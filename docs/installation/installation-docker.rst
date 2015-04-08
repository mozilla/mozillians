====================
Docker Installation
====================

Mozillians development environment can be installed using **docker**. This way we run Mozillians and all it's dependencies as docker containers. `Here <https://www.docker.com/whatisdocker/>`_ you can find more info about what docker is.

************
Dependencies
************

#. You need to install docker in your system. The `installation guide <https://docs.docker.com/installation/#installation>`_ covers many operating systems but for now we only support Linux and Mac OS X. *Version required*: 1.3.1 or newer.

#. We are using an orchestration tool for docker called `docker-compose <https://docs.docker.com/compose//>`_ that helps us automate the procedure of initiating our docker containers required for development. Installation instructions can be found `in Compose's documentation <https://docs.docker.com/compose/install/>`_. *Version required*: 1.0.1 or newer.

Running Docker on Mac
#####################

Here are some notes regarding running Docker on Mac.

* Docker cannot run natively on Mac because it is based in a Linux kernel specific featured called LXC.
* When running docker in Mac via **boot2docker** you are running a lightweight Linux VM in Virtualbox that hosts the docker daemon and the LXC containers.
* We are running docker client in our host system that connects to the docker daemon inside boot2docker VM.
* We are using docker's *volume sharing* feature in order to share the source code with the Mozillians container. This is not directly supported in Mac. As a workaround boot2docker implements this feature by sharing the folder with Virtualbox first.
* The extra layer that we are adding using Virtualbox might cause some performance issues. This is a trade-off for having an easily reproducible stack without installing everything manually.

More information regarding boot2docker can be found `in the documentation <https://docs.docker.com/installation/mac/>`_.

Here are some extra steps in order to run Mozillians on Mac:

#. Make sure *boot2docker* is initialized::

     $ boot2docker init

#. Make sure *boot2docker* VM is up and running::

     $ boot2docker up

#. Export *DOCKER_HOST* variables using the following command::

     $ $(boot2docker shellinit)

.. note::
   You need to make sure to run ``$(boot2docker shellinit)`` in each new shell you are using, or export it globally in order not to repeat this step every time you are working on mozillians.

*******************
Building mozillians
*******************
#. `Fork the main Mozillians repository <https://github.com/mozilla/mozillians>`_.
#. Clone your fork to your local machine::

     $ git clone --recursive git@github.com:YOUR_USERNAME/mozillians.git mozillians
     (lots of output - be patient...)
     $ cd mozillians

#. Configure your local Mozillians installation::

     $ cp mozillians/settings/local.py-docker-dist mozillians/settings/local.py

#. Start ``MySQL`` and ``ElasticSearch`` containers::

     $ docker-compose up -d db es

#. Update the product details::

     $ docker-compose run web python manage.py update_product_details -f

#. Create the database tables and run the migrations::

     $ docker-compose run web python manage.py syncdb --noinput --migrate

#. Load the timezone tables to MySQL::

     $ docker-compose run db /bin/bash
     shell> mysql_tzinfo_to_sql /usr/share/zoneinfo/ | mysql -uroot -proot -h db_1 mysql

#. Create user

   #. Run mozillians::

        docker-compose up

   #. Load http://127.0.0.1:8000 or (for Mac users only) ``<IP>:8000`` where ``<IP>`` is the one returned by ``boot2docker ip`` command.
   #. Sign in with persona to create your profile.
   #. Stop the server with ``Ctrl^C``.
   #. Vouch your account and convert it to superuser::

        docker-compose run web ./scripts/su.sh

      .. note::

         In case this command doesn't work, you can run ``./scripts/su.sh`` inside the container. In order to get shell access please run ``docker-compose run web /bin/bash``.

******************
Running mozillians
******************

#. Run Mozillians::

     $ docker-compose up
     (lots of output - be patient...)

#. Develop!
