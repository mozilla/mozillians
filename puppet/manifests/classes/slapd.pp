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
}