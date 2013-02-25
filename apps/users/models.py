import os
import uuid
from datetime import datetime

import pyes

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models
from django.db.models import signals as dbsignals
from django.dispatch import receiver

from elasticutils.contrib.django import S
from elasticutils.contrib.django.models import SearchMixin
from elasticutils.contrib.django import tasks as elasticutilstasks
from funfactory.urlresolvers import reverse
from PIL import Image, ImageOps
from product_details import product_details
from sorl.thumbnail import ImageField
from tower import ugettext as _, ugettext_lazy as _lazy

from apps.groups.models import (Group, GroupAlias,
                                Skill, SkillAlias,
                                Language, LanguageAlias)
from apps.phonebook.helpers import gravatar

from tasks import update_basket_task

COUNTRIES = product_details.get_regions('en-US')

USERNAME_MAX_LENGTH = 30
AVATAR_SIZE = (300, 300)


def _calculate_photo_filename(instance, filename):
    """Generate a unique filename for uploaded photo."""
    return os.path.join(settings.USER_AVATAR_DIR, str(uuid.uuid4()) + '.jpg')


class UserProfile(models.Model, SearchMixin):
    # This field is required.
    user = models.OneToOneField(User)
    full_name = models.CharField(max_length=255, default='', blank=False,
                                 verbose_name=_lazy(u'Full Name'))
    is_vouched = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True, default=datetime.now)
    website = models.URLField(max_length=200, verbose_name=_lazy(u'Website'),
                              default='', blank=True)
    vouched_by = models.ForeignKey('UserProfile', null=True, default=None,
                                   on_delete=models.SET_NULL, blank=True,
                                   related_name='vouchees')
    groups = models.ManyToManyField(Group, blank=True)
    skills = models.ManyToManyField(Skill, blank=True)
    languages = models.ManyToManyField(Language, blank=True)
    bio = models.TextField(verbose_name=_lazy(u'Bio'), default='', blank=True)
    photo = ImageField(default='', blank=True,
                       upload_to=_calculate_photo_filename)
    ircname = models.CharField(max_length=63,
                               verbose_name=_lazy(u'IRC Nickname'),
                               default='', blank=True)
    country = models.CharField(max_length=50, default='', blank=True,
                               choices=COUNTRIES.items(),
                               verbose_name=_lazy(u'Country'))
    region = models.CharField(max_length=255, default='', blank=True,
                              verbose_name=_lazy(u'Province/State'))
    city = models.CharField(max_length=255, default='', blank=True,
                            verbose_name=_lazy(u'City'))
    allows_community_sites = models.BooleanField(
        default=True,
        verbose_name=_lazy(u'Sites that can determine my vouched status'),
        choices=((True, _lazy(u'All Community Sites')),
                 (False, _lazy(u'Only Mozilla Properties'))))
    allows_mozilla_sites = models.BooleanField(
        default=True,
        verbose_name=_lazy(u'Allow Mozilla sites to access my profile data?'),
        choices=((True, _lazy(u'Yes')), (False, _lazy(u'No'))))
    basket_token = models.CharField(max_length=1024, default='', blank=True)

    @property
    def display_name(self):
        return self.full_name

    class Meta:
        db_table = 'profile'
        ordering = ['full_name']

    def __unicode__(self):
        """Return this user's name when their profile is called."""
        return self.display_name

    def get_absolute_url(self):
        return reverse('profile', args=[self.user.username])

    def anonymize(self):
        """Remove personal info from a user"""

        for name in ['first_name', 'last_name', 'email']:
            setattr(self.user, name, '')
        self.full_name = ''

        # Give a random username
        self.user.username = uuid.uuid4().hex[:30]
        self.user.is_active = False

        self.user.save()

        for f in self._meta.fields:
            if not f.editable or f.name in ['id', 'user']:
                continue

            if f.default == models.fields.NOT_PROVIDED:
                raise Exception('No default value for %s' % f.name)

            setattr(self, f.name, f.default)

        for f in self._meta.many_to_many:
            getattr(self, f.name).clear()

        self.save()

    def set_membership(self, model, membership_list):
        """Alters membership to Groups, Skills and Languages."""
        if model is Group:
            m2mfield = self.groups
            alias_model = GroupAlias
        elif model is Skill:
            m2mfield = self.skills
            alias_model = SkillAlias
        elif model is Language:
            m2mfield = self.languages
            alias_model = LanguageAlias

        # Remove any non-system groups that weren't supplied in this list.
        m2mfield.remove(*[g for g in m2mfield.all()
                          if g.name not in membership_list
                          and not getattr(g, 'system', False)])

        # Add/create the rest of the groups
        groups_to_add = []
        for g in membership_list:
            if alias_model.objects.filter(name=g).exists():
                group = alias_model.objects.get(name=g).alias
            else:
                group = model.objects.create(name=g)

            if not getattr(g, 'system', False):
                groups_to_add.append(group)

        m2mfield.add(*groups_to_add)

    def is_complete(self):
        """Tests if a user has all the information needed to move on
        past the original registration view.

        """
        return self.display_name.strip() != ''

    def photo_url(self):
        if self.photo:
            return self.photo.url

        return gravatar(self.user.email)

    def vouch(self, vouched_by, commit=True):
        if self.is_vouched:
            return

        self.is_vouched = True
        self.vouched_by = vouched_by

        if commit:
            self.save()

        self._email_now_vouched()

    def auto_vouch(self):
        """Auto vouch mozilla.com users."""
        email = self.user.email
        if any(email.endswith('@' + x) for x in settings.AUTO_VOUCH_DOMAINS):
            self.vouch(None, commit=False)

    def add_to_staff_group(self):
        """Keep users in the staff group if they're autovouchable."""
        email = self.user.email
        staff, created = Group.objects.get_or_create(name='staff', system=True)
        if any(email.endswith('@' + x) for x in
               settings.AUTO_VOUCH_DOMAINS):
            self.groups.add(staff)
        elif staff in self.groups.all():
            self.groups.remove(staff)

    def _email_now_vouched(self):
        """Email this user, letting them know they are now vouched."""
        subject = _(u'You are now vouched on Mozillians!')
        message = _(u"You've now been vouched on Mozillians.org. "
                     "You'll now be able to search, vouch "
                     "and invite other Mozillians onto the site.")
        send_mail(subject, message, 'no-reply@mozillians.org',
                  [self.user.email])

    @classmethod
    def extract_document(cls, obj_id, obj=None):
        """Method used by elasticutils."""
        if obj is None:
            obj = cls.objects.get(pk=obj_id)

        d = {}

        attrs = ('id', 'is_vouched', 'website', 'ircname',
                 'region', 'city', 'allows_mozilla_sites',
                 'allows_community_sites')
        for a in attrs:
            data = getattr(obj, a)
            if isinstance(data, basestring):
                data = data.lower()
            d.update({a: data})

        if obj.country:
            d.update({'country':
                      [obj.country, COUNTRIES[obj.country].lower()]})

        # user data
        attrs = ('username', 'email', 'last_login', 'date_joined')
        for a in attrs:
            data = getattr(obj.user, a)
            if isinstance(data, basestring):
                data = data.lower()
            d.update({a: data})

        d.update(dict(fullname=obj.full_name.lower()))
        d.update(dict(name=obj.full_name.lower()))
        d.update(dict(bio=obj.bio))
        d.update(dict(has_photo=bool(obj.photo)))

        for attribute in ['groups', 'skills', 'languages']:
            groups = []
            for g in getattr(obj, attribute).all():
                groups.extend(g.aliases.values_list('name', flat=True))
            d[attribute] = groups
        return d

    @classmethod
    def get_mapping(cls):
        """Returns an ElasticSearch mapping."""
        return {
            'properties': {
                'id': {'type': 'integer'},
                'name': {'type': 'string', 'index': 'not_analyzed'},
                'fullname': {'type': 'string', 'analyzer': 'standard'},
                'email': {'type': 'string', 'index': 'not_analyzed'},
                'ircname': {'type': 'string', 'index': 'not_analyzed'},
                'username': {'type': 'string', 'index': 'not_analyzed'},
                'country': {'type': 'string', 'analyzer': 'whitespace'},
                'region': {'type': 'string', 'analyzer': 'whitespace'},
                'city': {'type': 'string', 'analyzer': 'whitespace'},
                'skills': {'type': 'string', 'analyzer': 'whitespace'},
                'groups': {'type': 'string', 'analyzer': 'whitespace'},
                'languages': {'type': 'string', 'index': 'not_analyzed'},
                'bio': {'type': 'string', 'analyzer': 'snowball'},
                'is_vouched': {'type': 'boolean'},
                'allows_mozilla_sites': {'type': 'boolean'},
                'allows_community_sites': {'type': 'boolean'},
                'photo': {'type': 'boolean'},
                'website': {'type': 'string', 'index': 'not_analyzed'},
                'last_updated': {'type': 'date'},
                'date_joined': {'type': 'date'}}}

    @classmethod
    def search(cls, query, vouched=None, photo=None):
        """Sensible default search for UserProfiles."""
        query = query.lower().strip()
        fields = ('username', 'bio__text', 'email', 'ircname',
                  'country__text', 'country__text_phrase',
                  'region__text', 'region__text_phrase',
                  'city__text', 'city__text_phrase',
                  'fullname__text', 'fullname__text_phrase',
                  'fullname__prefix', 'fullname__fuzzy'
                  'groups__text')

        if query:
            q = dict((field, query) for field in fields)
            s = (S(cls)
                 .boost(fullname__text_phrase=5, username=5, email=5,
                        ircname=5, fullname__text=4, country__text_phrase=4,
                        region__text_phrase=4, city__text_phrase=4,
                        fullname__prefix=3, fullname__fuzzy=2,
                        bio__text=2)
                 .query(or_=q))
        else:
            s = S(cls)

        s = s.order_by('_score', 'name')

        if vouched is not None:
            s = s.filter(is_vouched=vouched)
        if photo is not None:
            s = s.filter(has_photo=photo)
        return s

    def save(self, *args, **kwargs):
        self.auto_vouch()
        super(UserProfile, self).save(*args, **kwargs)
        self.add_to_staff_group()


@receiver(dbsignals.post_save, sender=User,
          dispatch_uid='create_user_profile_sig')
def create_user_profile(sender, instance, created, raw, **kwargs):
    if not raw:
        up, created = UserProfile.objects.get_or_create(user=instance)
        if not created:
            dbsignals.post_save.send(sender=UserProfile, instance=up,
                                     created=created, raw=raw)


@receiver(dbsignals.post_save, sender=UserProfile,
          dispatch_uid='resize_photo_sig')
def resize_photo(sender, instance, **kwargs):
    if instance.photo:
        path = str(instance.photo.path)
        img = Image.open(path)
        if img.size != AVATAR_SIZE:
            img = ImageOps.fit(img, AVATAR_SIZE,
                               Image.ANTIALIAS, 0, (0.5, 0.5))
            img.save(path)


@receiver(dbsignals.post_save, sender=UserProfile,
          dispatch_uid='update_basket_sig')
def update_basket(sender, instance, **kwargs):
    update_basket_task.delay(instance.id)


@receiver(dbsignals.post_save, sender=UserProfile,
          dispatch_uid='update_search_index_sig')
def update_search_index(sender, instance, **kwargs):
    elasticutilstasks.index_objects.delay(sender, [instance.id])


@receiver(dbsignals.post_delete, sender=UserProfile,
          dispatch_uid='remove_from_search_index_sig')
def remove_from_search_index(sender, instance, **kwargs):
    try:
        elasticutilstasks.unindex_objects.delay(sender, [instance.id])
    except pyes.exceptions.ElasticSearchException, e:
        # Patch pyes
        if (e.status == 404 and
            isinstance(e.result, dict) and 'error' not in e.result):
            # Item was not found, but command did not return an error.
            # Do not worry.
            return
        else:
            raise e


class UsernameBlacklist(models.Model):
    value = models.CharField(max_length=30, unique=True)
    is_regex = models.BooleanField(default=False)

    def __unicode__(self):
        return self.value

    class Meta:
        ordering = ['value']
