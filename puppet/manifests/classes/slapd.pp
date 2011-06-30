# Get slapd up and slapping
class slapd {
    file { "$PROJ_DIR/directory/localtest/setup.sh":
        ensure => file,
        source => "$PROJ_DIR/puppet/files/directory/localtest/setup.sh";
    }
    file { "$PROJ_DIR/directory/localtest/slapd.conf":
        ensure => file,
        source => "$PROJ_DIR/puppet/files/directory/localtest/slapd.conf";
    }


# NOTE: BELOW IS mostly DOCS ONLY... I ended up doing this in the VM and then packaging
/*
     Centos only has OpenLDAP 2.3.43... what fun is that?
     package { "openldap-devel": ensure => installed; }
     package { "openldap": ensure => installed; }
     package { "openldap-clients": ensure => installed; }
     package { "openldap-servers": ensure => installed; }
     package { "openldap-servers-overlays": ensure => installed; }    

TODO no OpenSSL
wget http://www.openssl.org/source/openssl-0.9.8r.tar.gz
tar xfz openssl-0.9.8r.tar.gz 
cd openssl-0.9.8r
./configure && make && make test && sudo make install
TODO no Cyrus SASL
wget http://ftp.andrew.cmu.edu/pub/cyrus-mail/cyrus-sasl-2.1.21.tar.gz
tar xfz cyrus-sasl-2.1.21.tar.gz
cd cyrus-sasl-2.1.21
./configure && make && sudo make install && sudo ln -s /usr/local/lib/sasl2 /usr/lib/sasl2
slapd
ftp://ftp.openldap.org/pub/OpenLDAP/openldap-stable/openldap-stable-20100719.tgz
cd openldap-2.4.23
./configure --enable-overlays=yes
make depend
make
sudo yum install groff
sudo make install

# keep pip install happy
sudo ln -s /usr/local/include/sasl /usr/include/sasl

*/

}