# Get slapd up and slapping
class slapd {
    file { "$PROJ_DIR/directory/devslapd/setup.sh":
        ensure => file,
        source => "$PROJ_DIR/puppet/files/directory/devslapd/setup.sh";
    }
    file { "$PROJ_DIR/directory/devslapd/slapd.conf":
        ensure => file,
        source => "$PROJ_DIR/puppet/files/directory/devslapd/slapd.conf";
    }
}
