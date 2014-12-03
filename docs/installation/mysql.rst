.. mysql:

===========
MySQL setup
===========

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

    mysql> create database mozillians;

#. Give the mozillians user access to the mozillians database::

    mysql> GRANT ALL PRIVILEGES ON mozillians.* TO "mozillians"@"localhost";
    mysql> EXIT
    Bye
    $

.. _MySQL site: http://dev.mysql.com/downloads/mysql/
