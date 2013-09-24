import os
import uuid
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models
from django.db.models import signals as dbsignals
from django.dispatch import receiver

from elasticutils.contrib.django import S, get_es
from elasticutils.contrib.django.models import SearchMixin
from funfactory.urlresolvers import reverse
from product_details import product_details
from pytz import common_timezones
from sorl.thumbnail import ImageField, get_thumbnail
from south.modelsinspector import add_introspection_rules
from tower import ugettext as _, ugettext_lazy as _lazy

from mozillians.common.helpers import gravatar
from mozillians.groups.models import (Group, GroupAlias, Skill, SkillAlias,
                                      Language, LanguageAlias)
from mozillians.users.managers import (DEFAULT_PRIVACY_FIELDS, EMPLOYEES,
                                       MOZILLIANS, PRIVACY_CHOICES, PRIVILEGED,
                                       PUBLIC, PUBLIC_INDEXABLE_FIELDS,
                                       UserProfileManager)
from mozillians.users.tasks import (index_objects, remove_from_basket_task,
                                    update_basket_task, unindex_objects)


COUNTRIES = product_details.get_regions('en-US')
AVATAR_SIZE = (300, 300)


def _calculate_photo_filename(instance, filename):
    """Generate a unique filename for uploaded photo."""
    return os.path.join(settings.USER_AVATAR_DIR, str(uuid.uuid4()) + '.jpg')


class PrivacyField(models.PositiveSmallIntegerField):
    def __init__(self, *args, **kwargs):
        myargs = {'default': MOZILLIANS,
                  'choices': PRIVACY_CHOICES}
        myargs.update(kwargs)
        return super(PrivacyField, self).__init__(*args, **myargs)
add_introspection_rules([], ["^mozillians\.users\.models\.PrivacyField"])


class PrivacyAwareS(S):

    def privacy_level(self, level=MOZILLIANS):
        """Set privacy level for query set."""
        self._privacy_level = level
        return self

    def _clone(self, *args, **kwargs):
        new = super(PrivacyAwareS, self)._clone(*args, **kwargs)
        new._privacy_level = getattr(self, '_privacy_level', None)
        return new

    def __iter__(self):
        self._iterator = super(PrivacyAwareS, self).__iter__()
        def _generator():
            while True:
                obj = self._iterator.next()
                obj._privacy_level = getattr(self, '_privacy_level', None)
                yield obj
        return _generator()


class UserProfilePrivacyModel(models.Model):
    _privacy_fields = DEFAULT_PRIVACY_FIELDS
    _privacy_level = None

    privacy_photo = PrivacyField()
    privacy_full_name = PrivacyField()
    privacy_ircname = PrivacyField()
    privacy_email = PrivacyField()
    privacy_website = PrivacyField()
    privacy_bio = PrivacyField()
    privacy_city = PrivacyField()
    privacy_region = PrivacyField()
    privacy_country = PrivacyField()
    privacy_groups = PrivacyField()
    privacy_skills = PrivacyField()
    privacy_languages = PrivacyField()
    privacy_vouched_by = PrivacyField()
    privacy_date_mozillian = PrivacyField()
    privacy_timezone = PrivacyField()
    privacy_tshirt = PrivacyField(choices=((PRIVILEGED, 'Privileged'),),
                                  default=PRIVILEGED)
    privacy_title = PrivacyField()

    class Meta:
        abstract=True

class UserProfile(UserProfilePrivacyModel, SearchMixin):
    objects = UserProfileManager()

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
    date_vouched = models.DateTimeField(null=True, blank=True, default=None)
    groups = models.ManyToManyField(Group, blank=True, related_name='members')
    skills = models.ManyToManyField(Skill, blank=True, related_name='members')
    languages = models.ManyToManyField(Language, blank=True,
                                       related_name='members')
    bio = models.TextField(verbose_name=_lazy(u'Bio'), default='', blank=True)
    photo = ImageField(default='', blank=True,
                       upload_to=_calculate_photo_filename)
    ircname = models.CharField(max_length=63,
                               verbose_name=_lazy(u'IRC Nickname'),
                               default='', blank=True)
    country = models.CharField(max_length=50, default='',
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
    date_mozillian = models.DateField('When was involved with Mozilla',
                                      null=True, blank=True, default=None)
    timezone = models.CharField(max_length=100, blank=True, default='',
                                choices=zip(common_timezones, common_timezones))
    tshirt = models.IntegerField(
        _lazy(u'T-Shirt'), blank=True, null=True, default=None,
        choices=(
            (1, 'Fitted Small'), (2, 'Fitted Medium'),
            (3, 'Fitted Large'), (4, 'Fitted X-Large'),
            (5, 'Fitted XX-Large'), (6, 'Fitted XXX-Large'),
            (7, 'Straight-cut Small'), (8, 'Straight-cut Medium'),
            (9, 'Straight-cut Large'), (10, 'Straight-cut X-Large'),
            (11, 'Straight-cut XX-Large'), (12, 'Straight-cut XXX-Large')
        ))
    title = models.CharField(_lazy(u'What do you do for Mozilla?'),
                             max_length=70, blank=True, default='')

    class Meta:
        db_table = 'profile'
        ordering = ['full_name']

    def __getattribute__(self, attrname):
        _getattr = (lambda x:
                    super(UserProfile, self).__getattribute__(x))
        privacy_fields = _getattr('_privacy_fields')
        privacy_level = _getattr('_privacy_level')
        if privacy_level is not None and attrname in privacy_fields:
            field_privacy = _getattr('privacy_%s' % attrname)
            if field_privacy < privacy_level:
                return privacy_fields.get(attrname)
        return super(UserProfile, self).__getattribute__(attrname)

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
    def search(cls, query, include_non_vouched=False, public=False):
        """Sensible default search for UserProfiles."""
        query = query.lower().strip()
        fields = ('username', 'bio__text', 'email', 'ircname',
                  'country__text', 'country__text_phrase',
                  'region__text', 'region__text_phrase',
                  'city__text', 'city__text_phrase',
                  'fullname__text', 'fullname__text_phrase',
                  'fullname__prefix', 'fullname__fuzzy'
                  'groups__text')
        s = PrivacyAwareS(cls)
        if public:
            s = s.privacy_level(PUBLIC)
        s = s.indexes(cls.get_index(public))

        if query:
            q = dict((field, query) for field in fields)
            s = (s.boost(fullname__text_phrase=5, username=5, email=5,
                         ircname=5, fullname__text=4, country__text_phrase=4,
                         region__text_phrase=4, city__text_phrase=4,
                         fullname__prefix=3, fullname__fuzzy=2,
                         bio__text=2).query(or_=q))

        s = s.order_by('_score', 'name')

        if not include_non_vouched:
            s = s.filter(is_vouched=True)

        return s

    @property
    def accounts(self):
        if self._privacy_level:
            return self.externalaccount_set.filter(privacy__gte=self._privacy_level)
        return self.externalaccount_set.all()

    @property
    def email(self):
        """Privacy aware email property."""
        if self._privacy_level and self.privacy_email < self._privacy_level:
            return self._privacy_fields['email']
        return self.user.email

    @property
    def display_name(self):
        return self.full_name

    @property
    def privacy_level(self):
        """Return user privacy clearance."""
        if (self.groups.filter(name='privileged').exists() or self.user.is_superuser):
            return PRIVILEGED
        if self.groups.filter(name='staff').exists():
            return EMPLOYEES
        if self.is_vouched:
            return MOZILLIANS
        return PUBLIC

    @property
    def is_complete(self):
        """Tests if a user has all the information needed to move on
        past the original registration view.

        """
        return self.display_name.strip() != ''

    @property
    def is_public(self):
        """Return True is any of the privacy protected fields is PUBLIC."""
        for field in self._privacy_fields:
            if getattr(self, 'privacy_%s' % field, None) == PUBLIC:
                return True
        return False

    @property
    def is_public_indexable(self):
        """For profile to be public indexable should have at least
        full_name OR ircname OR email set to PUBLIC.

        """
        for field in PUBLIC_INDEXABLE_FIELDS:
            if (getattr(self, 'privacy_%s' % field, None) == PUBLIC and
                getattr(self, field, None)):
                return True
        return False

    def __unicode__(self):
        """Return this user's name when their profile is called."""
        return self.display_name

    def get_absolute_url(self):
        return reverse('phonebook:profile_view', args=[self.user.username])

    def set_instance_privacy_level(self, level):
        """Sets privacy level of instance."""
        self._privacy_level = level

    def set_privacy_level(self, level, save=True):
        """Sets all privacy enabled fields to 'level'."""
        for field in self._privacy_fields:
            setattr(self, 'privacy_%s' % field, level)
        if save:
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

            if not getattr(group, 'system', False):
                groups_to_add.append(group)

        m2mfield.add(*groups_to_add)

    def get_photo_thumbnail(self, geometry='160x160', **kwargs):
        if 'crop' not in kwargs:
            kwargs['crop'] = 'center'
        if self.photo:
            return get_thumbnail(self.photo, geometry, **kwargs)
        return get_thumbnail(settings.DEFAULT_AVATAR_PATH, geometry, **kwargs)

    def get_photo_url(self, geometry='160x160', **kwargs):
        """Return photo url.

        If privacy allows and no photo set, return gravatar link.
        If privacy allows and photo set return local photo link.
        If privacy doesn't allow return default local link.
        """
        privacy_level = getattr(self, '_privacy_level', MOZILLIANS)
        if (not self.photo and self.privacy_photo >= privacy_level):
            return gravatar(self.user.email, size=geometry)
        return self.get_photo_thumbnail(geometry, **kwargs).url

    def vouch(self, vouched_by, commit=True):
        if self.is_vouched:
            return

        self.is_vouched = True
        self.vouched_by = vouched_by
        self.date_vouched = datetime.now()

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
        elif self.groups.filter(pk=staff.pk).exists():
            self.groups.remove(staff)

    def _email_now_vouched(self):
        """Email this user, letting them know they are now vouched."""
        subject = _(u'You are now vouched on Mozillians!')
        message = _(u"You've now been vouched on Mozillians.org. "
                     "You'll now be able to search, vouch "
                     "and invite other Mozillians onto the site.")
        send_mail(subject, message, settings.FROM_NOREPLY,
                  [self.user.email])

    def save(self, *args, **kwargs):
        self._privacy_level = None
        self.auto_vouch()
        super(UserProfile, self).save(*args, **kwargs)
        self.add_to_staff_group()

    @classmethod
    def get_index(cls, public_index=False):
        if public_index:
            return settings.ES_INDEXES['public']
        return settings.ES_INDEXES['default']

    @classmethod
    def refresh_index(cls, timesleep=0, es=None, public_index=False):
        if es is None:
            es = get_es()

        es.refresh(cls.get_index(public_index), timesleep=timesleep)

    @classmethod
    def index(cls, document, id_=None, bulk=False, force_insert=False,
              es=None, public_index=False):
        """ Overide elasticutils.index() to support more than one index
        for UserProfile model.

        """
        if bulk and es is None:
            raise ValueError('bulk is True, but es is None')

        if es is None:
            es = get_es()

        es.index(document, index=cls.get_index(public_index),
                 doc_type=cls.get_mapping_type(),
                 id=id_, bulk=bulk, force_insert=force_insert)

    @classmethod
    def unindex(cls, id, es=None, public_index=False):
        if es is None:
            es = get_es()

        es.delete(cls.get_index(public_index), cls.get_mapping_type(), id)


@receiver(dbsignals.post_save, sender=User,
          dispatch_uid='create_user_profile_sig')
def create_user_profile(sender, instance, created, raw, **kwargs):
    if not raw:
        up, created = UserProfile.objects.get_or_create(user=instance)
        if not created:
            dbsignals.post_save.send(sender=UserProfile, instance=up,
                                     created=created, raw=raw)


@receiver(dbsignals.post_save, sender=UserProfile,
          dispatch_uid='update_basket_sig')
def update_basket(sender, instance, **kwargs):
    update_basket_task.delay(instance.id)


@receiver(dbsignals.post_save, sender=UserProfile,
          dispatch_uid='update_search_index_sig')
def update_search_index(sender, instance, **kwargs):
    if instance.is_complete:
        index_objects.delay(sender, [instance.id], public_index=False)
        if instance.is_public_indexable:
            index_objects.delay(sender, [instance.id], public_index=True)
        else:
            unindex_objects.delay(UserProfile, [instance.id], public_index=True)


@receiver(dbsignals.pre_delete, sender=UserProfile,
          dispatch_uid='remove_from_search_index_sig')
def remove_from_search_index(sender, instance, **kwargs):
    unindex_objects.delay(UserProfile, [instance.id], public_index=False)
    unindex_objects.delay(UserProfile, [instance.id], public_index=True)

@receiver(dbsignals.pre_delete, sender=User,
          dispatch_uid='remove_from_basket_sig')
def remove_from_basket(sender, instance, **kwargs):
    remove_from_basket_task.delay(instance.email,
                                  instance.userprofile.basket_token)


class UsernameBlacklist(models.Model):
    value = models.CharField(max_length=30, unique=True)
    is_regex = models.BooleanField(default=False)

    def __unicode__(self):
        return self.value

    class Meta:
        ordering = ['value']


class ExternalAccount(models.Model):
    ACCOUNT_TYPES = {
        0:{'name': 'Mozilla Add-ons', 'url': 'https://addons.mozilla.org/user/{username}/'},
        # All bugs assigned to or reported by the user.
        1:{'name': 'Bugzilla', 'url': ('https://bugzilla.mozilla.org/'
                                       'buglist.cgi?emailtype1=exact'
                                       '&query_format=advanced'
                                       '&emailassigned_to1=1'
                                       '&email1={username}')},
        2:{'name': 'Github', 'url': 'https://github.com/{username}'},
        3:{'name': 'MDN', 'url': 'https://developer.mozilla.org/profiles/{username}'},
        4:{'name': 'Mozilla Support', 'url': ''},
        5:{'name': 'Facebook', 'url': 'https://www.facebook.com/{username}'},
        6:{'name': 'Twitter', 'url': 'https://twitter.com/{username}'},
        7:{'name': 'AIM', 'url': ''},
        8:{'name': 'Google Talk', 'url': ''},
        9:{'name': 'Skype', 'url': ''},
        10:{'name': 'Yahoo!', 'url': ''},
    }
    user = models.ForeignKey(UserProfile)
    username = models.CharField(max_length=255, verbose_name=_lazy('Account Username'))
    type = models.PositiveIntegerField(
        choices=sorted([(k, v['name'])
                        for (k, v) in ACCOUNT_TYPES.iteritems()], key=lambda x: x[1]),
        verbose_name=_lazy('Account Type'))
    privacy = models.PositiveIntegerField(default=MOZILLIANS,
                                          choices=PRIVACY_CHOICES)

    def get_username_url(self):
        return self.ACCOUNT_TYPES[self.type]['url'].format(username=self.username)
