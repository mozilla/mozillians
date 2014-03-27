#!/bin/sh

INSTANCE=generic
DB=mozillians_org
DEVDB=sanitize_dev_$DB
STAGEDB=sanitize_stage_$DB
cd /data/backups/bin/
rm -f anonymize.py anonymize_dev.yml anonymize_stage.yml
/usr/bin/wget -q --no-check-certificate -nH https://raw.github.com/mozilla/mozillians/master/scripts/mysql-anonymize/anonymize.py
/bin/chmod 755 anonymize.py
/usr/bin/wget -q --no-check-certificate -nH https://raw.github.com/mozilla/mozillians/master/scripts/mysql-anonymize/anonymize_dev.yml
/usr/bin/wget -q --no-check-certificate -nH https://raw.github.com/mozilla/mozillians/master/scripts/mysql-anonymize/anonymize_stage.yml

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
/usr/bin/mysqldump $DEVDB -u root $P -S /var/lib/mysql/$INSTANCE.sock > $SQLPATH/$DB.$TODAY.sanitized_dev.sql
/usr/bin/mysqldump $STAGEDB -u root $P -S /var/lib/mysql/$INSTANCE.sock > $SQLPATH/$DB.$TODAY.sanitized_stage.sql

# copy dbs
/usr/bin/scp -q $SQLPATH/$DB.$TODAY.sanitized_dev.sql $SQLPATH/$DB.$TODAY.sanitized_stage.sql  dev1.db.phx1.mozilla.com:/data/backup-drop/$INSTANCE/$DB

# Done!
