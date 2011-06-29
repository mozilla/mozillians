#
# Playdoh puppet magic for dev boxes
#
import "classes/*.pp"

$PROJ_DIR = "/vagrant"

$DB_NAME = "playdoh"
$DB_USER = "playdoh"
$DB_PASS = "playdoh"

$USE_YUM_CACHE_ON_HOST = 0
$USE_SOUTH = 0

class dev {
    class {
        dev_hacks: before => Class[repos];
        repos: before => Class[dev_tools];
        dev_tools: before => Class[mysql];
        mysql: before => Class[python];
        python: before => Class[apache];
        apache: before => Class[playdoh_site];
        playdoh_site: ;
    }
}

include dev
