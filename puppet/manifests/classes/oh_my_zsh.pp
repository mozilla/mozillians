class oh_my_zsh {
    exec { "oh-my-zsh":
        command => "wget --no-check-certificate https://github.com/robbyrussell/oh-my-zsh/raw/master/tools/install.sh -O - | sh",
        require => Package['git-core', 'zsh'],
        cwd => '/home/vagrant/',
        user => 'vagrant';
        #path => "/usr/bin:/usr/sbin:/bin:/usr/local/bin",
        #refreshonly => true,
    }

    exec { "change-shell":
        command => "sudo chsh vagrant -s /usr/bin/zsh",
        require => Exec['oh-my-zsh'];
    }
}
