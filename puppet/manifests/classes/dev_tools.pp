# Ensure some handy dev tools are available.
class dev_tools {
    case $operatingsystem {
        centos: {
            package {
                [ "git", "vim-enhanced" ]:
                ensure => installed;
            }
        }

        ubuntu: {
            package {
                [ "git-core", "vim", "emacs", "zsh" ]:
                ensure => installed;
            }
        }

    }
}
