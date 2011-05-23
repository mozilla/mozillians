# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is Domesday.
#
# The Initial Developer of the Original Code is
# The Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#   The Original Software was written to the Glory of God by 
#   Gervase Markham <written.to.the.glory.of.God@gerv.net>.
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****

import ldapdb
from ldapdb.models.fields import CharField, IntegerField, ImageField, ListField

import django
from django.db import models

import re
import sys
from commons.helpers import url


class Tag(ldapdb.models.Model):
    """
    A Domesday tag.
    """
    base_dn        = "ou=tags,dc=mozillians,dc=org"
    object_classes = ['groupOfNames']
    
    name        = CharField(db_column='cn', max_length=32768, primary_key=True)
    members     = ListField(db_column='member')
    description = CharField(db_column='description', max_length=1024)
    
    # Will eventually need a blesstag, and a field describing how to become
    # blessed.
    
    def members_as_people(self):
        # XXX want to say: 
        # return [Person.objects.get(dn=dn) for dn in self.members]
        return [Person.objects.get(uid=dn.split(',')[0].split("=")[1]) 
                for dn in self.members]

    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name
        

# Create your models here.
class Person(ldapdb.models.Model):
    """
    A Domesday person.
    """
    base_dn        = "ou=people,dc=mozillians,dc=org"
    object_classes = ['inetOrgPerson', 'domesdayPerson']

    uid          = IntegerField(db_column='uid', max_length=256, 
                                primary_key=True)

    # Other fields to consider include:
    # timezone
    # lat/long (with UI to help users specify with an appropriate degree of
    #           vagueness)
    
    cn           = CharField(db_column='cn', max_length=32768)
    name         = CharField(db_column='displayName', max_length=32768)    
    familyName   = CharField(db_column='sn', max_length=32768)
    nickname     = CharField(db_column='domesdayNickName', max_length=32768)
        
    address      = CharField(db_column='postalAddress', max_length=1024)
    locality     = CharField(db_column='l', max_length=32768)
    country      = CharField(db_column='co', max_length=32768)
    
    phone        = CharField(db_column='telephoneNumber', max_length=32768)
    title        = CharField(db_column='title', max_length=32768)
    bio          = CharField(db_column='description', max_length=1024)
    email        = CharField(db_column='mail', max_length=256)
    urls         = ListField(db_column='labeledURI')
    startyear = IntegerField(db_column='domesdayStartYear', max_length=32768)
    tshirtsize   = CharField(db_column='domesdayTShirtSize', max_length=32768)
    
    password     = CharField(db_column='userPassword', max_length=128)
    
    photo        = ImageField(db_column='jpegPhoto')
    
    def get_tags(self):
        tags = Tag.objects.filter(members__contains=self.dn)
        return [t.name for t in tags]
    
    def set_tags(self, tags):
        # Create Tag objects for each tag in the list (new ones 
        # if necessary) and make sure the user is a member of all of them.
        for tag in tags:
            try:
                t = Tag.objects.get(name=tag)
            except Tag.DoesNotExist:
                t = Tag(name=tag)
                
            if not self.dn in t.members:
                t.members.append(self.dn)
                t.save()
        
        # Remove user from tags which were not specified
        current_tags = Tag.objects.filter(members__contains=self.dn)

        for ct in current_tags:
            if not ct.name in tags:
              if len(ct.members) == 1:
                # They are the only person left with this tag
                ct.delete()
              else:
                ct.members.remove(self.dn)
                ct.save()

    tags = property(get_tags, set_tags)

    def get_accounts(self):
        accts = Account.scoped("uid=%s,%s" % (self.uid, Account.base_dn))
        return accts.objects.all().values()

    def set_accounts(self, accounts):
        # Create Account objects for each account in the list (new ones 
        # if necessary).
        MyAccount = Account.scoped("uid=%s,%s" % (self.uid, 
                                                  Account.base_dn))
        current_accts = MyAccount.objects.all()
        
        """
        XXX FilterExceptions...
        
        for a in accounts:
            try:
                ca = MyAccount.objects.get(domain=a['domain'])
                ca.userid = a['userid']
            except MyAccount.DoesNotExist:
                ca = MyAccount(domain=a['domain'], userid=a['userid'])
            ca.save()
        """
        
        # Remove user from accounts which were not specified
        account_domains = [a['domain'] for a in accounts]
            
        for ca in current_accts:
            if not ca.domain in account_domains:
                ca.delete()
        
    accounts = property(get_accounts, set_accounts)
    
    def get_userid(self, domain):
        accts = Account.scoped("uid=%s,%s" % (self.uid, Account.base_dn))
        account = accts.objects.filter(domain=domain)
        if account:
            return account[0].userid
        else:
            return None

    # This returns an object whose layout matches the PortableContacts schema
    # http://portablecontacts.net/draft-spec.html (retrieved 2011-04-19)
    # XXX Need to check doc more carefully and make sure it actually does in 
    # every respect.
    def json_struct(self):
        json_struct = {
            "displayName": self.name,
            "name": {
                "formatted": self.name,
                "familyName": self.familyName,
            },
            "nickname": self.nickname or "",
            "id": self.uid
        }
        
        if self.tags:
            json_struct["tags"] = [tag for tag in self.tags]
      
        if self.email:
            json_struct["emails"] = [{
                "value": self.email,
                "primary": "true"
            }]
        
        if self.urls:
            json_struct["urls"] = [{ 
                "value": u,
                "type": "other"
            } for u in self.urls]
              
        if self.phone:
            json_struct["phoneNumbers"] = [{
                "value": self.phone
            }]
      
        if self.photo:
            json_struct["photos"] = [{
                # XXX not an absolute URL, only site-relative
                "value": url('domesday.views.photo', pk=self.uid),
                "type": "thumbnail"
            }]
      
        if self.address or self.locality or self.country:
            json_struct["addresses"] = [{
                "streetAddress": self.address or "",
                "locality": self.locality or "",
                "country": self.country or "",
                "formatted": self.address + "\n" + self.country
            }]
      
        if self.accounts:
            json_struct["accounts"] = [{ 
                "domain": a['domain'], 
                "userid": a['userid'] 
            } for a in self.accounts]
            
        return json_struct
    
    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

    def save(self, using=None):
        # Make sure all required fields are populated (sn and cn)
        if not self.familyName:
            self.familyName = " "
        if not self.cn:
            self.cn = self.familyName
        
        super(Person, self).save(using)
        

class Account(ldapdb.models.Model):
    """
    An account on another system.
    
    To get the accounts for just a single person, use the scoped() method
    to add the person's Domesday uid, e.g.:
    Account.scoped("uid=%s,%s" % (self.uid, Account.base_dn))
    """
    base_dn        = "ou=people,dc=mozillians,dc=org"
    object_classes = ['account']

    domain = CharField(db_column='host', max_length=256, primary_key=True)
    userid = CharField(db_column='uid', max_length=256)

    def _get_owner(self):
        uid = re.search(',uid=(\d+),', self.dn).group(1)
        p = Person.objects.filter(pk=uid)
        return p
    
    owner = property(_get_owner)
        
    def __str__(self):
        return "%s: %s" % (self.domain, self.userid)

    def __unicode__(self):
        return "%s: %s" % (self.domain, self.userid)


class AccountType(django.db.models.Model):
    """
    The definition of an account type - domain and title. These are stored
    in the database, as they are just a helper for users and a way of making
    sure people are consistent about which domain is used for which service.
    """
    domain = django.db.models.CharField(max_length=128, primary_key=True)
    title = django.db.models.CharField(max_length=128)

    class Meta:
        ordering = ["title"]
    
    @classmethod
    def as_dict(cls):
        return dict([(a['domain'], a['title']) 
                     for a in cls.objects.all().values()])
        
    def __str__(self):
        return self.domain

    def __unicode__(self):
        return self.domain

