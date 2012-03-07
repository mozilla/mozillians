#
# Playdoh puppet magic for dev boxes
#
import "classes/*.pp"

$PROJ_DIR = "/home/vagrant/mozillians"

$DB_NAME = "mozillians"
$DB_USER = "mozillians"
$DB_PASS = "mozillians"

$USE_YUM_CACHE_ON_HOST = 0
$USE_SOUTH = 1

$DONT_REPROVISION = 1

Exec {
    path => "/usr/local/bin:/usr/bin:/usr/sbin:/sbin:/bin",
}

class dev {
    class {
        init: before => Class[dev_hacks];
        dev_hacks: before => Class[repos];
        repos: before => Class[dev_tools];
        dev_tools: before => Class[mysql];
        mysql: before => Class[python];
        python: before => Class[apache];
        apache: before => Class[playdoh_site];
        memcached:;
        playdoh_site:;
        elasticsearch: version => "0.18.6";
        # oh_my_zsh:;
    }
}

if $DONT_REPROVISION == 1 {
    file { "$PROJ_DIR/settings/local.py":
        ensure => file,
        source => "$PROJ_DIR/settings/local.py-dist";
    }

    file { "/home/vagrant/.zshrc":
        ensure => file,
        source => "$PROJ_DIR/puppet/files/home/vagrant/zshrc",
        owner => "vagrant", group => "vagrant", mode => 0644;
    }

    # TODO: make this support centos or ubuntu (#centos)
    exec { "sql_migrate":
        cwd => "$PROJ_DIR", 
        command => "/usr/bin/python2.6 manage.py syncdb --noinput",
    }

    if $USE_SOUTH == 1 {
        exec { "south_migrate":
            cwd => "$PROJ_DIR", 
            command => "/usr/bin/python2.6 manage.py migrate",
            require => Exec["sql_migrate"],
        }
    }
} else {
    include dev
}

exec { "es-restart":
    command => "/usr/local/elasticsearch/bin/service/elasticsearch restart",
    #path => "/usr/bin:/usr/sbin:/bin:/usr/local/bin",
    #refreshonly => true,
}
