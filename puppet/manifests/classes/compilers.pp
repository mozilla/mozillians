# TODO - put this into the VM, not puppet
class compilers {
    package { "gcc-c++": ensure => installed; }
}