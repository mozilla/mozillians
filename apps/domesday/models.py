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

    cn           = CharField(db_column='cn', max_length=32768)
    name         = CharField(db_column='displayName', max_length=32768)    
    familyName   = CharField(db_column='sn', max_length=32768)
    nickname     = CharField(db_column='domesdayNickName', max_length=32768)
        
    address      = CharField(db_column='postalAddress', max_length=1024)
    locality     = CharField(db_column='l', max_length=32768)
    country    = CharField(db_column='co', max_length=32768)
    
    phone      = CharField(db_column='telephoneNumber', max_length=32768)
    title        = CharField(db_column='title', max_length=32768)
    bio          = CharField(db_column='description', max_length=1024)
    email        = CharField(db_column='mail', max_length=256)
    startyear  = IntegerField(db_column='domesdayStartYear', max_length=32768)
    tshirtsize = CharField(db_column='domesdayTShirtSize', max_length=32768)
    
    password     = CharField(db_column='userPassword', max_length=128)
    
    photo        = ImageField(db_column='jpegPhoto')
    
    # Hmm - what is the proper API here? Return dicts, QuerySets or something
    # else? QuerySets are not iterable... :-(
    def get_tags(self):
        tags = Tag.objects.filter(members__contains=self.dn)
        return tags.objects.all().values()
    
    def set_tags(self, tags):
        # Create Tag objects for each tag in the list (new ones 
        # if necessary) and make sure the user is a member of all of them.
        pass

    tags = property(get_tags, set_tags)

    def get_accounts(self):
        accts = Account.scoped("uid=%s,%s" % (self.uid, Account.base_dn))
        return accts.objects.all().values()

    def set_accounts(self, accounts):
        pass
        
    accounts = property(get_accounts, set_accounts)
    
    def get_userid(self, domain):
        accts = Account.scoped("uid=%s,%s" % (self.uid, Account.base_dn))
        account = accts.objects.filter(domain=domain)
        if account:
            return account[0].userid
        else:
            return None
        
    # Blog and website are stored as labeledURI fields, with the labels 'blog'
    # and 'website'. This means we need some mapping.
    labeledURIs = ListField(db_column='labeledURI')
    
    def _get_uri(self, tag):
        test = re.compile("^(.*) " + tag + "$")
        results = filter(test.search, self.labeledURIs)
        if len(results):
            return test.match(results[0]).group(1)
        else:
            return ""
        
    def _set_uri(self, tag, value):
        # Extract the old version, if present
        test = re.compile("^(.*) " + tag + "$")
        results = filter(lambda u: not test.search(u), self.labeledURIs)
        # Add the new one
        results.append(value + " " + tag)
        self.labeledURIs = results
        return self._get_uri(tag)
    
    def _get_website(self):
        return self._get_uri("website")
        
    def _set_website(self, website):
        return self._set_uri("website", website)
    
    website = property(_get_website, _set_website)
    
    def _get_blog(self):
        return self._get_uri("blog")
        
    def _set_blog(self, blog):
        return self._set_uri("blog", blog)
        
    blog = property(_get_blog, _set_blog)
            
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
            json_struct["tags"] = [tag.name for tag in self.tags]
      
        if self.email:
            json_struct["emails"] = [{
                "value": self.email,
                "primary": "true"
            }]
        
        if self.blog or self.website:
            json_struct["urls"] = []
        
            if self.blog:
                json_struct["urls"].append({
                    "value": self.blog,
                    "type": "blog"
                }) 
            
            if self.website:
                json_struct["urls"].append({
                    "value": self.website,
                    "type": "home"
                })
      
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

