.. _ldap:
==============
OpenLDAP Notes
==============

Dumping data
------------

You can dump your directory by doing ::

    slapcat -l mozillians_backup.ldif

Or to only dump a specific directory::

    slapcat -b 'dc=mozillians,dc=org' -l mozillians_backup.ldif

Recreate a directory
--------------------
Want to start with a fresh directory?::

    sudo slapd stop
    sudo cd /var/lib/ldap/
    sudo rm -f __db* log* *.bdb
    sudo slapd start
    # install basic schemas (Step 5)
    # install domesday schema (Step 6)
    # refresh test data (Step 7)

You can be more selective by figuring out which database ({0} or {1}) and
then nuking only ``/var.lib/ldap/__db.00{n}``.

Importing a dump
----------------

You can import data::

    sudo ldapadd -c -l mozillians_backup.ldif
