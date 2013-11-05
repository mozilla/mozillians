#!/usr/bin/env python
# This assumes an id on each field.
import logging
import hashlib
import random


log = logging.getLogger('anonymize')
common_hash_secret = "%016x" % (random.getrandbits(128))


def get_truncates(config):
    database = config.get('database', {})
    truncates = database.get('truncate', [])
    sql = []
    for truncate in truncates:
        sql.append('TRUNCATE %s' % truncate)
    return sql


def get_deletes(config):
    database = config.get('database', {})
    tables = database.get('tables', [])
    sql = []
    for table, data in tables.iteritems():
        if 'delete' in data:
            fields = []
            for f, v in data['delete'].iteritems():
                fields.append('%s = "%s"' % (f, v))
            statement = 'DELETE FROM %s WHERE ' % table + ' AND '.join(fields)
            sql.append(statement)
    return sql

listify = lambda x: x if isinstance(x, list) else [x]

def get_updates(config):
    global common_hash_secret

    database = config.get('database', {})
    tables = database.get('tables', [])
    sql = []
    for table, data in tables.iteritems():
        updates = []
        for operation, details in data.iteritems():
            if operation == 'nullify':
                for field in listify(details):
                    updates.append("%s = NULL" % field)
            elif operation == 'random_int':
                for field in listify(details):
                    updates.append("%s = ROUND(RAND()*1000000)" % field)
            elif operation == 'random_ip':
                for field in listify(details):
                    updates.append("%s = INET_NTOA(RAND()*1000000000)" % field)
            elif operation == 'random_email':
                for field in listify(details):
                    updates.append("%s = CONCAT(id, '@mozilla.com')"
                                   % field)
            elif operation == 'random_username':
                for field in listify(details):
                    updates.append("%s = CONCAT('_user_', id)" % field)
            elif operation == 'hash_value':
                for field in listify(details):
                    updates.append("%(field)s = MD5(CONCAT(@common_hash_secret, %(field)s))"
                                   % dict(field=field))
            elif operation == 'hash_email':
                for field in listify(details):
                    updates.append("%(field)s = CONCAT(MD5(CONCAT(@common_hash_secret, %(field)s)), '@mozilla.com')"
                                   % dict(field=field))
            elif operation == 'delete':
                continue
            else:
                log.warning('Unknown operation.')
        if updates:
            sql.append('UPDATE %s SET %s' % (table, ', '.join(updates)))
    return sql


def anonymize(config):
    database = config.get('database', {})
    
    if 'name' in database:
         print "USE %s;" % database['name']

    print "SET FOREIGN_KEY_CHECKS=0;"
    
    sql = []
    sql.extend(get_truncates(config))
    sql.extend(get_deletes(config))
    sql.extend(get_updates(config))
    for stmt in sql:
        print stmt + ';'

    print "SET FOREIGN_KEY_CHECKS=1;"
    print

if __name__ == '__main__':
    
    import yaml
    import sys

    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = [ 'anonymize.yml' ]

    for f in files:
        print "--"
        print "-- %s" %f
        print "--"
        print "SET @common_hash_secret=rand();"
        print ""
        cfg = yaml.load(open(f))
        if 'databases' not in cfg:
            anonymize(cfg)
        else:
            databases = cfg.get('databases')
            for name, sub_cfg in databases.items():
                print "USE %s;" % name
                anonymize({'database': sub_cfg})
