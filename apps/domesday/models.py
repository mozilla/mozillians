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
    
    name    = CharField(db_column='cn', max_length=32768, primary_key=True)
    members = ListField(db_column='member')

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
    givenName    = CharField(db_column='givenName', max_length=32768)
    familyName   = CharField(db_column='sn', max_length=32768)
    name         = CharField(db_column='displayName', max_length=32768)    
    nickname     = CharField(db_column='domesdayNickName', max_length=32768)
    
    title        = CharField(db_column='title', max_length=32768)    
    address      = CharField(db_column='postalAddress', max_length=1024)
    locality     = CharField(db_column='l', max_length=32768)
    bio          = CharField(db_column='description', max_length=1024)
    email        = CharField(db_column='mail', max_length=256)
    # XXX Do we need a PasswordField type?
    password     = CharField(db_column='userPassword', max_length=128)
    
    photo        = ImageField(db_column='jpegPhoto')
    
    def get_tags(self):
        return Tag.objects.filter(members__contains=self.dn)
    
    def set_tags(self):
        pass

    tags = property(get_tags, set_tags)
    
    # Blog and website are stored as labeledURI fields, with the labels 'blog'
    # and 'website'. This means we need some mapping.
    labeledURIs = ListField(db_column='labeledURI')
    
    def get_uri(self, tag):
        test = re.compile("^(.*) " + tag + "$")
        results = filter(test.search, self.labeledURIs)
        if len(results):
            return test.match(results[0]).group(1)
        else:
            return ""
        
    def set_uri(self, tag, value):
        # Extract the old version, if present
        test = re.compile("^(.*) " + tag + "$")
        results = filter(lambda u: not test.search(u), self.labeledURIs)
        # Add the new one
        results.append(value + " " + tag)
        self.labeledURIs = results
        return self.get_uri(tag)
    
    def get_website(self):
        return self.get_uri("website")
        
    def set_website(self, website):
        return self.set_uri("website", website)
    
    website = property(get_website, set_website)
    
    def get_blog(self):
        return self.get_uri("blog")
        
    def set_blog(self, blog):
        return self.set_uri("blog", blog)
        
    blog = property(get_blog, set_blog)
    
    country    = CharField(db_column='co', max_length=32768)
    phone      = CharField(db_column='telephoneNumber', max_length=32768)
    tshirtsize = CharField(db_column='domesdayTShirtSize', max_length=32768)
    startyear  = IntegerField(db_column='domesdayStartYear', max_length=32768)
    
    # XXX accounts/system IDs

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
                "givenName": self.givenName or ""
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
      
      # "accounts": [
      #  {% for a in self.accounts %}
      #    {% if not forlooself.first %}, {% endif %}
      #    {
      #      "domain": a.domain,
      #      "userid": a.user
      #    }
      #  {% endfor %}
      #],      
        
        return json_struct
    
    def __str__(self):
        return self.name

    def __unicode__(self):
        return self.name

class ServiceDefinition(django.db.models.Model):
    domain = django.db.models.CharField(max_length=128, primary_key=True)
    title = django.db.models.CharField(max_length=128)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.domain

    def __unicode__(self):
        return self.domain

