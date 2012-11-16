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
from elasticutils.contrib.django import tasks
from funfactory.urlresolvers import reverse
from PIL import Image, ImageOps
from product_details import product_details
from sorl.thumbnail import ImageField
from tower import ugettext as _, ugettext_lazy as _lazy

from apps.groups.models import Group, Skill, Language
from apps.phonebook.helpers import gravatar

# This is because we are using MEDIA_ROOT wrong in 1.4
from django.core.files.storage import FileSystemStorage
fs = FileSystemStorage(location=settings.UPLOAD_ROOT,
                       base_url='/media/uploads/')

COUNTRIES = product_details.get_regions('en-US')

USERNAME_MAX_LENGTH = 30
AVATAR_SIZE = (300, 300)


class UserProfile(models.Model, SearchMixin):
    # This field is required.
    user = models.OneToOneField(User)

    full_name = models.CharField(max_length=255, default='', blank=True,
                                verbose_name=_lazy(u'Full Name'))
    is_vouched = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True, default=datetime.now)
    website = models.URLField(max_length=200, verbose_name=_lazy(u'Website'),
                              default='', blank=True, null=True)
    vouched_by = models.ForeignKey('UserProfile', null=True, default=None,
                                   on_delete=models.SET_NULL, blank=True)
    groups = models.ManyToManyField(Group, blank=True)
    skills = models.ManyToManyField(Skill, blank=True)
    languages = models.ManyToManyField(Language, blank=True)
    bio = models.TextField(verbose_name=_lazy(u'Bio'), default='', blank=True)
    photo = ImageField(default='', blank=True, storage=fs,
                       upload_to='userprofile')
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

    @property
    def display_name(self):
        return self.full_name

    class Meta:
        db_table = 'profile'

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
        elif model is Skill:
            m2mfield = self.skills
        elif model is Language:
            m2mfield = self.languages

        # Remove any non-system groups that weren't supplied in this list.
        m2mfield.remove(*[g for g in m2mfield.all()
                                if g.name not in membership_list
                                and not getattr(g, 'system', False)])

        # Add/create the rest of the groups
        groups_to_add = []
        for g in membership_list:
            (group, created) = model.objects.get_or_create(name=g)

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
            d.update({'country': COUNTRIES[obj.country].lower()})

        # user data
        attrs = ('username', 'email', 'last_login', 'date_joined')
        for a in attrs:
            data = getattr(obj.user, a)
            if isinstance(data, basestring):
                data = data.lower()
            d.update({a: data})

        d.update(dict(name=obj.full_name.lower()))
        d.update(dict(fullname=obj.full_name.lower()))
        d.update(dict(bio=obj.bio))
        d.update(dict(has_photo=bool(obj.photo)))
        # Index groups, skills, and languages ... for fun.
        d.update(dict(groups=list(obj.groups.values_list('name', flat=True))))
        d.update(dict(skills=list(obj.skills.values_list('name', flat=True))))
        d.update(dict(languages=list(obj.languages.values_list('name',
                                                               flat=True))))

        return d

    @classmethod
    def get_mapping(cls):
        """Returns an ElasticSearch mapping."""
        return {
            'properties': {
                'id': {'type': 'integer'},
                # The name is a name---so we shouldn't analyze it
                # (de-stem, tokenize, parse, etc).
                'name': {'type': 'string', 'analyzer': 'whitespace'},
                'fullname': {'type': 'string', 'index': 'not_analyzed'},
                'email': {'type': 'string', 'index': 'not_analyzed'},
                'ircname': {'type': 'string', 'index': 'not_analyzed'},
                'username': {'type': 'string', 'index': 'not_analyzed'},
                'country': {'type': 'string', 'index': 'not_analyzed'},
                'region': {'type': 'string', 'index': 'not_analyzed'},
                'city': {'type': 'string', 'index': 'not_analyzed'},
                'skills': {'type': 'string', 'index': 'not_analyzed'},
                'groups': {'type': 'string', 'index': 'not_analyzed'},
                'languages': {'type': 'string', 'index': 'not_analyzed'},

                # The bio has free-form text in it, so analyze it with
                # snowball.
                'bio': {'type': 'string', 'analyzer': 'snowball'},

                'is_vouched': {'type': 'boolean'},
                'allows_mozilla_sites': {'type': 'boolean'},
                'allows_community_sites': {'type': 'boolean'},
                'photo': {'type': 'boolean'},

                # The website also shouldn't be analyzed.
                'website': {'type': 'string', 'index': 'not_analyzed'},

                # The last_updated field is a date.
                'last_updated': {'type': 'date'},
                'date_joined': {'type': 'date'}}}

    @classmethod
    def search(cls, query, vouched=None, photo=None):
        """Sensible default search for UserProfiles."""
        query = query.lower().strip()
        fields = ('username', 'bio__text', 'website', 'email', 'groups',
                  'skills', 'languages', 'name__prefix', 'ircname',
                  'country', 'region', 'city', 'fullname__prefix')

        if query:
            q = dict((field, query) for field in fields)
            s = S(cls).query(or_=q)
        else:
            s = S(cls)

        if vouched is not None:
            s = s.filter(is_vouched=vouched)
        if photo is not None:
            s = s.filter(has_photo=photo)
        return s


@receiver(dbsignals.post_save, sender=User,
          dispatch_uid='create_user_profile_sig')
def create_user_profile(sender, instance, created, raw, **kwargs):
    if not raw:
        up, created = UserProfile.objects.get_or_create(user=instance)
        if not created:
            dbsignals.post_save.send(sender=UserProfile, instance=up,
                                     created=created, raw=raw)


@receiver(dbsignals.pre_save, sender=UserProfile,
          dispatch_uid='auto_vouch_sig')
def auto_vouch(sender, instance, raw, using, **kwargs):
    """Auto vouch mozilla.com users."""
    if not instance.id and not raw:
        email = instance.user.email
        if any(email.endswith('@' + x) for x in settings.AUTO_VOUCH_DOMAINS):
            instance.vouch(None, commit=False)


@receiver(dbsignals.post_save, sender=UserProfile,
          dispatch_uid='add_to_staff_group_sig')
def add_to_staff_group(sender, instance, created, raw, **kwargs):
    """Keep users in the staff group if they're autovouchable."""
    if raw:
        return
    email = instance.user.email
    staff, created = Group.objects.get_or_create(name='staff', system=True)
    if any(email.endswith('@' + x) for x in
           settings.AUTO_VOUCH_DOMAINS):
        instance.groups.add(staff)
    elif staff in instance.groups.all():
        instance.groups.remove(staff)


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
          dispatch_uid='update_search_index_sig')
def update_search_index(sender, instance, **kw):
    tasks.index_objects.delay(sender, [instance.id])


@receiver(dbsignals.post_delete, sender=UserProfile,
          dispatch_uid='remove_from_search_index_sig')
def remove_from_search_index(sender, instance, **kw):
    try:
        tasks.unindex_objects.delay(sender, [instance.id])
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
