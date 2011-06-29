# Ensure some handy dev tools are available.
class dev_tools {
    package { 
        [ "git", "vim-enhanced" ]:
            ensure => installed;
    }
}
