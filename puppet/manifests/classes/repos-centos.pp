# Ensure all necessary package repos are available.

class repos {

    case $operatingsystem {
        centos: {
            # Make sure we've got EPEL for extra packages
            $epel_url = "http://download.fedora.redhat.com/pub/epel/5/x86_64/epel-release-5-4.noarch.rpm"
            exec { "repo_epel":
                command => "/bin/rpm -Uvh $epel_url",
                creates => '/etc/yum.repos.d/epel.repo'
                #require => File["/etc/yum.conf"]
            }

        }
    }

}
