import ldapdb

from ldapdb.models.fields import CharField, ImageField

class Person(ldapdb.models.Model):
    base_dn        = "ou=people,dc=mozillians,dc=org"
    object_classes = ['inetOrgPerson', 'mozilliansPerson']

    # uid in LDAP is an email address used in the login form
    email      = CharField(db_column='uid', max_length=256, 
                                primary_key=True)

    # permenant random string, used globally on the backend
    stable_uid = CharField(db_column='uniqueIdentifier', max_length=32768)

    cn         = CharField(db_column='cn', max_length=32768)
    full_name  = CharField(db_column='displayName', max_length=32768)
    photo      = ImageField(db_column='jpegPhoto')
