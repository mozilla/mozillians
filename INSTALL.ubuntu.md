See INSTALL for basic instructions. Below are specific installation instructions for Ubuntu 10.04 or later. 

Application to other systems is currently an exercise for the reader :-) Patches welcome!

1) Install Python 2.6+, MySQL 5+, pip

    sudo apt-get install libmysqlclient-dev python-pip python-jinja2 python-mysqldb python-dev libsasl2-dev libldap2-dev libssl-dev mysql-server subversion

Optional: Python's virtualenv
    sudo python-virtualenv

4) Confirm the OpenLDAP server is installed (slapd)

The directory depends on Berkley DB utils, such as db4.2-util in Ubuntu 9.04 or db4.7-util in 10.04. This command should add that dependency automagically.

    sudo apt-get install slapd ldap-utils 

The command 

    ps aux | grep slap

should show the directory running. If not, start it.

5) Ensure standard schemas are already loaded

    sudo ldapadd -Y EXTERNAL -H ldapi:/// -f /etc/ldap/schema/cosine.ldif
    sudo ldapadd -Y EXTERNAL -H ldapi:/// -f /etc/ldap/schema/nis.ldif
    sudo ldapadd -Y EXTERNAL -H ldapi:/// -f /etc/ldap/schema/inetorgperson.ldif

    sudo ldapadd -Y EXTERNAL -H ldapi:/// -f directory/domesday-schema.ldif

6) Set up directory structure and root DN access for Mozillians.

    sudo ldapadd -Y EXTERNAL -H ldapi:/// -f directory/mozillians-config.ldif

7) Put test Mozillians data in directory

    sudo ldapadd -x -D cn=admin,dc=mozillians,dc=org -W -f directory/mozillians-data.ldif