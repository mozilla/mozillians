# Get apache up and running

class apache {
    package { "httpd-devel": 
        ensure => present,
        before => File['/etc/httpd/conf.d/playdoh-site.conf']; 
    }
    file { "/etc/httpd/conf.d/playdoh-site.conf":
        source  => "$PROJ_DIR/puppet/files/etc/httpd/conf.d/playdoh-site.conf",
        owner   => "root", group => "root", mode => 0644,
        require => [ Package['httpd-devel'] ];
    }
    service { "httpd":
        ensure    => running,
        enable    => true,
        require   => [
            Package['httpd-devel'],
            File['/etc/httpd/conf.d/playdoh-site.conf']
        ]
        #subscribe => File['/etc/httpd/conf.d/playdoh-site.conf']
    }
}
