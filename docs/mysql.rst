.. mysql:

===========
MySQL setup
===========

Setting up a MySQL user and database for development:

#. Install the `MySQL server`_.

.. _MySQL server: http://dev.mysql.com/downloads/mysql/

#. Start the mysql client program as the mysql root user::

    $ mysql -u root -p
    Enter password: ........
    mysql>

#. Create a ``mozillians`` user::

    mysql> create user 'mozillians'@'localhost';

#. Create a ``mozillians`` database::

    mysql> create database mozillians;

#. Give the mozillians user access to the mozillians database::

    mysql> GRANT ALL PRIVILEGES ON mozillians.* TO "mozillians"@"localhost";
    mysql> EXIT
    Bye
    $
