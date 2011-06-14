= OpenLDAP Notes =
The following notes are MySQL speak for LDAP Directory servers.

== mysqldump ==
slapcat -l mozillains_backup.ldif

Or to only dump a specific directory:

slapcat -b 'dc=mozillians,dc=org' -l mozillians_backup.ldif

== drop database foo; create database foo; ==
Want to start with a fresh directory?

    sudo slapd stop
    sudo cd /var/lib/ldap/
    sudo rm -f __db* log* *.bdb
    sudo slapd start
    # install basic schemas (Step 5)
    # install domesday schema (Step 6)
    # refresh test data (Step 7)

You can be more selective by figuring out which database ({0} or {1}) and 
then nuking only /var.ib/ldap/__db.00{n}.

== mysql < dump.sql ==

    sudo ldapadd -c -l mozillians_backup.ldif