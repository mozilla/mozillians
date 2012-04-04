# Do some dirty, dirty things to make development nicer.
class dev_hacks {

    file { "$PROJ_DIR/settings/local.py":
        ensure => file,
        source => "$PROJ_DIR/settings/local.py-dist";
    }

    file { "/home/vagrant/.bashrc_vagrant":
        ensure => file,
        source => "$PROJ_DIR/puppet/files/home/vagrant/bashrc_vagrant",
        owner => "vagrant", group => "vagrant", mode => 0644;
    }

    # Put our custom bash commands in a separate file.
    exec { "amend_rc":
        command => "echo 'if [ -f /home/vagrant/.bashrc_vagrant ] && ! shopt -oq posix; then . /home/vagrant/.bashrc_vagrant; fi' >> /home/vagrant/.bashrc"
    }

    file { "/home/vagrant/.zshrc":
        ensure => file,
        source => "$PROJ_DIR/puppet/files/home/vagrant/zshrc",
        owner => "vagrant", group => "vagrant", mode => 0644;
    }

    case $operatingsystem {

        centos: {

            if $USE_YUM_CACHE_ON_HOST == 1 {
                # TODO: IS THIS REALLY A GOOD IDEA?!
                # In order to speed up destroying and building CentOS boxes,
                # move and retain the yum-cache onto the host side.
                exec { "copy_yum_cache":
                    command => "/bin/cp -r /var/cache/yum $PROJ_DIR/puppet/cache/",
                    unless  => "/bin/ls $PROJ_DIR/puppet/cache/yum"
                }
                file { "/etc/yum.conf":
                    source  => "$PROJ_DIR/puppet/files/etc/yum.conf",
                    owner => "root", group => "root",
                    require => Exec["copy_yum_cache"]
                }
            }

            # Disable SELinux... causing problems, and I don't understand it.
            # TODO: see http://blog.endpoint.com/2010/02/selinux-httpd-modwsgi-26-rhel-centos-5.html
            file { "/etc/selinux/config":
                source => "/home/vagrant/mozillians/puppet/files/etc/selinux/config",
                owner => "root", group => "root", mode => 0644;
            }
            #exec { "disable_selinux_enforcement":
            #    command => "/usr/sbin/setenforce 0",
            #    unless => "/usr/sbin/getenforce | grep -q 'Disabled'";
            #}

        }

    }

}
