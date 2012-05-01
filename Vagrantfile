require "yaml"

# Load up our vagrant config files -- vagrantconfig.yaml first
_config = YAML.load(File.open(File.join(File.dirname(__FILE__),
                    "vagrantconfig.yaml"), File::RDONLY).read)

# Local-specific/not-git-managed config -- vagrantconfig_local.yaml
begin
  _config.merge!(YAML.load(File.open(File.join(File.dirname(__FILE__),
                 "vagrantconfig_local.yaml"), File::RDONLY).read))
rescue Errno::ENOENT # No vagrantconfig_local.yaml found -- that's OK; just
                     # use the defaults.
end

CONF = _config
MOUNT_POINT = '/home/vagrant/mozillians'

Vagrant::Config.run do |config|
    config.vm.box = "mozillians-v1.0"
    config.vm.box_url = "http://people.mozilla.org/~mmacpherson/mozillians-v1.0.box"

    config.vm.forward_port 8000, 8000

    # Increase vagrant's patience during hang-y CentOS bootup
    # see: https://github.com/jedi4ever/veewee/issues/14
    config.ssh.max_tries = 50
    config.ssh.timeout   = 300

    # nfs needs to be explicitly enabled to run.
    if CONF['nfs'] == false or RUBY_PLATFORM =~ /mswin(32|64)/
        config.vm.share_folder("v-root", MOUNT_POINT, ".")
    else
        config.vm.share_folder("v-root", MOUNT_POINT, ".", :nfs => true)
    end

    # This keeps it from pegging your CPU
    # um, doesn't work... in .8.10...
    # config.vm.customize ["modifyvm", :id, "--cpuexecutioncap", "90"]

    # Add to /etc/hosts: 33.33.33.24 dev.mozillians.org
    config.vm.network :hostonly, "33.33.33.24"

    config.vm.provision :puppet do |puppet|
        puppet.manifests_path = "puppet/manifests"
        puppet.manifest_file  = "dev-vagrant.pp"
        puppet.module_path = "puppet/modules"
    end
end
