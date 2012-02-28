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

Exec { path => [ "/bin/"] }

class dev {
    class {
        dev_hacks: before => Class[repos];
        repos: before => Class[dev_tools];
        dev_tools: before => Class[mysql];
        mysql: before => Class[python];
        python: before => Class[apache];
        apache: before => Class[playdoh_site];
        memcached:;
        playdoh_site:;
        elasticsearch: version => "0.18.6";
    }
}

include dev
