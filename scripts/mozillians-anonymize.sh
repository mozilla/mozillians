#!/bin/sh

INSTANCE=generic
DB=mozillians_org
DEVDB=sanitize_dev_$DB
DEVDB_SANITIZED=sanitized_dev_$DB
STAGEDB=sanitize_stage_$DB
STAGEDB_SANITIZED=sanitized_stage_$DB
cd /data/backups/bin/sanitize
rm -f anonymize.py anonymize_dev.yml anonymize_stage.yml
/usr/bin/wget -q -nH https://raw.github.com/mozilla/mozillians/master/scripts/mysql-anonymize/anonymize.py
/bin/chmod 755 anonymize.py
/usr/bin/wget -q -nH https://raw.github.com/mozilla/mozillians/master/scripts/mysql-anonymize/anonymize_dev.yml
/usr/bin/wget -q -nH https://raw.github.com/mozilla/mozillians/master/scripts/mysql-anonymize/anonymize_stage.yml

TODAY=`/bin/date +"%Y.%m.%d"`
HOSTNAME=`/bin/hostname`
SQLPATH=/data-2/$HOSTNAME/backups/$INSTANCE/sqlcopies/$DB
SQLFILE=$SQLPATH/$DB.$TODAY.sql
PASS=`/bin/grep ^password /data/$INSTANCE/$INSTANCE.cnf | /bin/cut -f2 -d= | /usr/bin/uniq`
if [ $PASS == ""]
then
P=""
else
P="-p$PASS"
fi

MYSQL="/usr/bin/mysql --defaults-file=/data/$INSTANCE/$INSTANCE.cnf -S /var/lib/mysql/$INSTANCE.sock"

# Delete and recreate sanitized dbs
$MYSQL -e "drop database if exists $DEVDB_SANITIZED"
$MYSQL -e "create database if not exists $DEVDB_SANITIZED"
$MYSQL -e "drop database if exists $STAGEDB_SANITIZED"
$MYSQL -e "create database if not exists $STAGEDB_SANITIZED"


# import db
$MYSQL -e "drop database if exists $DEVDB"
$MYSQL -e "create database if not exists $DEVDB"
$MYSQL $DEVDB < $SQLFILE

$MYSQL -e "drop database if exists $STAGEDB"
$MYSQL -e "create database if not exists $STAGEDB"
$MYSQL $STAGEDB < $SQLFILE

# sanitize dbs
/usr/bin/python anonymize.py anonymize_dev.yml > $SQLPATH/$DB.$TODAY.queries_sanitize_dev.sql
$MYSQL $DEVDB < $SQLPATH/$DB.$TODAY.queries_sanitize_dev.sql

/usr/bin/python anonymize.py anonymize_stage.yml > $SQLPATH/$DB.$TODAY.queries_sanitize_stage.sql
$MYSQL $STAGEDB < $SQLPATH/$DB.$TODAY.queries_sanitize_stage.sql

# export dbs
/usr/bin/mysqldump $DEVDB_SANITIZED -u root $P -S /var/lib/mysql/$INSTANCE.sock > $SQLPATH/$DB.$TODAY.sanitized_dev.sql
/usr/bin/mysqldump $STAGEDB_SANITIZED -u root $P -S /var/lib/mysql/$INSTANCE.sock > $SQLPATH/$DB.$TODAY.sanitized_stage.sql

# copy dbs
# copy dbs; compress for the copy only
gzip $SQLPATH/$DB.$TODAY.sanitized_dev.sql $SQLPATH/$DB.$TODAY.sanitized_stage.sql
/usr/bin/scp $SQLPATH/$DB.$TODAY.sanitized_dev.sql.gz genericadm.private.phx1.mozilla.com:/data/genericrhel6-dev/src/mozillians-dev.allizom.org/mozillians/media/mozillians_org.latest.sanitized_dev.sql.gz
# stage goes to dev-db, an LDAP-protected dir
/usr/bin/scp $SQLPATH/$DB.$TODAY.sanitized_stage.sql.gz genericadm.private.phx1.mozilla.com:/data/genericrhel6-dev/src/mozillians-dev.allizom.org/mozillians/media/dev-db/mozillians_org.latest.sanitized_stage.sql.gz
# leave this uncompressed for more efficient storage on our backup device (yes, really)
gunzip $SQLPATH/$DB.$TODAY.sanitized_dev.sql.gz $SQLPATH/$DB.$TODAY.sanitized_stage.sql.gz            

# Done!
