# Class: elasticsearch
#
# This class installs Elasticsearch
#
# Usage:
# include elasticsearch


define download_file($site="", $cwd="") {
    exec { $name:
           command => "wget ${site}/${name}",
           cwd => $cwd,
           creates => "${cwd}/${name}",
           path => ["/bin", "/usr/bin"],
    }
}

class sun_java_6 {

  # $release = regsubst(generate("/usr/bin/lsb_release", "-s", "-c"), '(\w+)\s', '\1')

  # file { "partner.list":
  #   path => "/etc/apt/sources.list.d/partner.list",
  #   ensure => file,
  #   owner => "root",
  #   group => "root",
  #   content => "deb http://archive.canonical.com/ $release partner\ndeb-src http://archive.canonical.com/ $release partner\n",
  #   notify => Exec["apt-get-update"],
  #   require => Exec['add-java'],
  # }

  # exec { "add-java":
  #   command => "sudo add-apt-repository ppa:ferramroberto/java",
  #   #path => "/usr/bin:/usr/sbin:/bin:/usr/local/bin",
  #   #refreshonly => true,
  # }

  exec { "apt-get-update":
    command => "/usr/bin/apt-get update",
    refreshonly => true,
  }

  package { ["debconf-utils", "openjdk-6-jre-headless"]:
    ensure => installed
  }

  # exec { "agree-to-jdk-license":
  #   command => "/bin/echo -e sun-java6-jdk shared/accepted-sun-dlj-v1-1 select true | debconf-set-selections",
  #   unless => "debconf-get-selections | grep 'sun-java6-jdk.*shared/accepted-sun-dlj-v1-1.*true'",
  #   path => ["/bin", "/usr/bin"], require => Package["debconf-utils"],
  # }

  # exec { "agree-to-jre-license":
  #   command => "/bin/echo -e sun-java6-jre shared/accepted-sun-dlj-v1-1 select true | debconf-set-selections",
  #   unless => "debconf-get-selections | grep 'sun-java6-jre.*shared/accepted-sun-dlj-v1-1.*true'",
  #   path => ["/bin", "/usr/bin"], require => Package["debconf-utils"],
  # }

  # package { "sun-java6-jdk":
  #   ensure => latest,
  #   require => [ File["partner.list"], Exec["agree-to-jdk-license"], Exec["apt-get-update"] ],
  # }

  # package { "sun-java6-jre":
  #   ensure => latest,
  #   require => [ File["partner.list"], Exec["agree-to-jre-license"], Exec["apt-get-update"] ],
  # }

}

class elasticsearch($version = "0.15.2", $xmx = "2048m") {
      $esBasename       = "elasticsearch"
      $esName           = "${esBasename}-${version}"
      $esFile           = "${esName}.tar.gz"
      $esServiceName    = "${esBasename}-servicewrapper"
      $esServiceFile    = "${esServiceName}.tar.gz"
      $esPath           = "${ebs1}/usr/local/${esName}"
      $esPathLink       = "/usr/local/${esBasename}"
      $esDataPath       = "${ebs1}/var/lib/${esBasename}"
      $esLibPath        = "${esDataPath}"
      $esLogPath        = "${ebs1}/var/log/${esBasename}"
      $esXms            = "256m"
      $esXmx            = "${xmx}"
      $cluster          = "${esBasename}"
      $esTCPPortRange   = "9300-9399"
      $esHTTPPortRange  = "9200-9299"
      $esUlimitNofile   = "32000"
      $esUlimitMemlock  = "unlimited"
      $esPidpath        = "/var/run"
      $esPidfile        = "${esPidpath}/${esBasename}.pid"
      $esJarfile        = "${esName}.jar"
      $esServiceRev     = "3e0b23d"

      # include sun_java_6

      download_file {
        ["${esName}.tar.gz"]:
        site => "https://github.com/downloads/elasticsearch/elasticsearch",
        cwd => "/tmp/",
      }

      download_file {
        ["$esServiceRev"]:
        site => "https://github.com/elasticsearch/elasticsearch-servicewrapper/tarball",
        cwd => "/tmp/",
        alias => "download wrapper"
      }

      # Ensure the elasticsearch user is present
      user { "$esBasename":
               ensure => "present",
               comment => "Elasticsearch user created by puppet",
               managehome => true,
               shell   => "/bin/false",
               #require => [Package["sun-java6-jre"]],
               uid => 901
     }

     file { "/etc/security/limits.d/${esBasename}.conf":
            content => template("elasticsearch/elasticsearch.limits.conf.erb"),
            ensure => present,
            owner => root,
            group => root,
     }

     exec { "mkdir-ebs-mongohome":
          path => "/bin:/usr/bin",
          command => "mkdir -p $ebs1/usr/local",
          before => File["$esPath"],
          require => User["$esBasename"]
     }

     # Make sure we have the application path
     file { "$esPath":
             ensure     => directory,
             require    => User["$esBasename"],
             owner      => "$esBasename",
             group      => "$esBasename",
             recurse    => true
      }

      # Remove old files and copy in latest
      exec { "elasticsearch-mkpath":
             path => "/bin:/usr/bin",
             command => "mkdir -p $esPath",
      }

      exec { "elasticsearch-untar":
             path => "/bin:/usr/bin",
             command => "tar -xzf /tmp/$esFile -C /tmp",
             require => Download_File["$esFile"]
      }

      exec { "elasticsearch-package":
             path => "/bin:/usr/bin",
             command => "sudo -u$esBasename cp -rf /tmp/$esName/. $esPath/.",
             unless  => "test -f $esPath/bin/elasticsearch",
             require => [Exec["elasticsearch-mkpath"],
                         Exec["elasticsearch-untar"],
                         User["$esBasename"],
                        ],
             notify => Service["$esBasename"],
      }

      ## Note: this is a bit hackish, need to stop the old elasticsearch when upgrading
      exec { "stop-elasticsearch-version-change":
           command => "service elasticsearch stop",
           unless => "ps aux | grep ${esName} | grep -v grep",
           onlyif => "ps aux | grep ${esBasename} | grep -v grep",
           require => Exec["elasticsearch-package"],
           notify => Service["$esBasename"]
      }

      # Create link to /usr/local/<esBasename> which will be the current version
      file { "$esPathLink":
           ensure => link,
           target => "$esPath",
           require => Exec["stop-elasticsearch-version-change"]

      }

      # Ensure the data path is created
      file { "$esDataPath":
           ensure => directory,
           owner  => "$esBasename",
           group  => "$esBasename",
           require => Exec["elasticsearch-package"],
           recurse => true
      }

      # Ensure the link to the data path is set
      file { "$esPath/data":
           ensure => link,
           force => true,
           target => "$esDataPath",
           require => File["$esDataPath"]
      }

      # Symlink config to /etc
      file { "/etc/$esBasename":
             ensure => link,
             target => "$esPathLink/config",
             require => Exec["elasticsearch-package"],
      }

      # Apply config template for search
      file { "$esPath/config/elasticsearch.yml":
             content => template("elasticsearch/elasticsearch.yml.erb"),
             require => File["/etc/$esBasename"]
      }

      # Stage the Service Package
      file { "/tmp/$esServiceFile":
           source => "/tmp/$esServiceRev",
           require => [
             Exec["elasticsearch-package"],
             Download_File["download wrapper"]
           ]
      }

      # Move the service wrapper into place
      exec { "elasticsearch-service":
             path => "/bin:/usr/bin",
             unless => "test -d $esPath/bin/service/lib",
             command => "tar -xzf /tmp/$esServiceFile -C /tmp && mv /tmp/elasticsearch-$esServiceName-$esServiceRev/service $esPath/bin && rm /tmp/$esServiceFile",
             require => [File["/tmp/$esServiceFile"], User["$esBasename"]]
      }

      # Ensure the service is present
      file { "$esPath/bin/service":
           ensure => directory,
           owner  => elasticsearch,
           group  => elasticsearch,
           recurse => true,
           require => Exec["elasticsearch-service"]
      }

      # Set the service config settings
      file { "$esPath/bin/service/elasticsearch.conf":
             content => template("elasticsearch/elasticsearch.conf.erb"),
             require => File["$esPath/bin/service"]
      }

      # Add customized startup script (see: http://www.elasticsearch.org/tutorials/2011/02/22/running-elasticsearch-as-a-non-root-user.html)
      file { "$esPath/bin/service/elasticsearch":
             source => "puppet:///modules/elasticsearch/elasticsearch",
             require => File["$esPath/bin/service"]
      }

      # Create startup script
      file { "/etc/init.d/elasticsearch":
             ensure => link,
             target => "$esPath/bin/service/./elasticsearch",
             require => [Exec["stop-elasticsearch-version-change"], File["$esPath/bin/service/elasticsearch"]]
      }

      # Ensure logging directory
      file { "$esLogPath":
           owner     => "$esBasename",
           group     => "$esBasename",
           ensure    => directory,
           recurse   => true,
           require   => Exec["elasticsearch-package"],
      }

      file { "$esPath/logs":
           ensure => link,
           target => "/var/log/$esBasename",
           force => true,
           require => File["/var/log/$esBasename"]
      }

      # Ensure the service is running
      service { "$esBasename":
            enable => true,
            ensure => running,
            hasrestart => true,
            require => File["$esPath/logs"]
      }

}
