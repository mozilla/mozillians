# Things to do that make playdoh go.

class playdoh_site {

    # TODO: Need a more puppety way to do this.
    exec { "create_mysql_database":
        command => "/usr/bin/mysqladmin -uroot create $DB_NAME",
        unless  => "/usr/bin/mysql -uroot -B --skip-column-names -e 'show databases' | /bin/grep '$DB_NAME'",
    }
    
    # TODO: Need a more puppety way to do this.
    exec { "grant_mysql_database":
        command => "/usr/bin/mysql -uroot -B -e'GRANT ALL PRIVILEGES ON $DB_NAME.* TO $DB_USER@localhost IDENTIFIED BY \"$DB_PASS\"'",
        unless  => "/usr/bin/mysql -uroot -B --skip-column-names mysql -e 'select user from user' | /bin/grep '$DB_USER'",
        require => Exec["create_mysql_database"]
    }

}
