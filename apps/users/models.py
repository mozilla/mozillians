import os
import uuid
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models
from django.db.models import Q
from django.db.models import signals as dbsignals
from django.db.models.query import QuerySet, ValuesQuerySet
from django.dispatch import receiver

from elasticutils.contrib.django import S, get_es
from elasticutils.contrib.django.models import SearchMixin
from funfactory.urlresolvers import reverse
from product_details import product_details
from sorl.thumbnail import ImageField, get_thumbnail
from tower import ugettext as _, ugettext_lazy as _lazy

from apps.common.helpers import gravatar
from apps.groups.models import (Group, GroupAlias,
                                Skill, SkillAlias,
                                Language, LanguageAlias)


from tasks import update_basket_task, index_objects, unindex_objects

COUNTRIES = product_details.get_regions('en-US')

USERNAME_MAX_LENGTH = 30
AVATAR_SIZE = (300, 300)

PRIVILEGED = 1
EMPLOYEES = 2
MOZILLIANS = 3
PUBLIC = 4
PRIVACY_CHOICES = (# (PRIVILEGED, 'Privileged'),
                   # (EMPLOYEES, 'Employees'),
                   (MOZILLIANS, 'Mozillians'),
                   (PUBLIC, 'Public'))
PUBLIC_INDEXABLE_FIELDS = ['full_name', 'ircname', 'email']


def _calculate_photo_filename(instance, filename):
    """Generate a unique filename for uploaded photo."""
    return os.path.join(settings.USER_AVATAR_DIR, str(uuid.uuid4()) + '.jpg')


class UserProfileValuesQuerySet(ValuesQuerySet):
    """Custom ValuesQuerySet to support privacy.

    Note that when you specify fields in values() you need to include
    the related privacy field in your query.

    E.g. .values('first_name', 'privacy_first_name')

    """

    def _clone(self, *args, **kwargs):
        c = super(UserProfileValuesQuerySet, self)._clone(*args, **kwargs)
        c._privacy_level = getattr(self, '_privacy_level', None)
        return c

    def iterator(self):
        # Purge any extra columns that haven't been explicitly asked for
        extra_names = self.query.extra_select.keys()
        field_names = self.field_names
        aggregate_names = self.query.aggregate_select.keys()

        names = extra_names + field_names + aggregate_names

        privacy_fields = [
            (names.index('privacy_%s' % field), names.index(field), field)
            for field in set(UserProfile._privacy_fields) & set(names)]

        for row in self.query.get_compiler(self.db).results_iter():
            row = list(row)
            for levelindex, fieldindex, field in privacy_fields:
                if row[levelindex] < self._privacy_level:
                    row[fieldindex] = UserProfile._privacy_fields[field]
            yield dict(zip(names, row))


class UserProfileQuerySet(QuerySet):
    """Custom QuerySet to support privacy."""

    def __init__(self, *args, **kwargs):
        self.public_q = Q()
        for field in UserProfile._privacy_fields:
            key = 'privacy_%s' % field
            self.public_q |= Q(**{key: PUBLIC})

        self.public_index_q = Q()
        for field in PUBLIC_INDEXABLE_FIELDS:
            key = 'privacy_%s' % field
            if field == 'email':
                field = 'user__email'
            self.public_index_q |= (Q(**{key: PUBLIC}) & ~Q(**{field: ''}))

        return super(UserProfileQuerySet, self).__init__(*args, **kwargs)

    def privacy_level(self, level=MOZILLIANS):
        """Set privacy level for query set."""
        self._privacy_level = level
        return self.all()

    def public(self):
        """Return profiles with at least one PUBLIC field."""
        return self.filter(self.public_q)

    def vouched(self):
        """Return complete and vouched profiles."""
        return self.complete().filter(is_vouched=True)

    def complete(self):
        """Return complete profiles."""
        return self.exclude(full_name='')

    def public_indexable(self):
        """Return public indexable profiles."""
        return self.complete().filter(self.public_index_q)

    def not_public_indexable(self):
        return self.complete().exclude(self.public_index_q)

    def _clone(self, *args, **kwargs):
        """Custom _clone with privacy level propagation."""
        if kwargs.get('klass', None) == ValuesQuerySet:
            kwargs['klass'] = UserProfileValuesQuerySet
        c = super(UserProfileQuerySet, self)._clone(*args, **kwargs)
        c._privacy_level = getattr(self, '_privacy_level', None)
        return c

    def iterator(self):
        """Custom QuerySet iterator which sets privacy level in every
        object returned.

        """

        def _generator():
            self._iterator = super(UserProfileQuerySet, self).iterator()
            while True:
                obj = self._iterator.next()
                obj._privacy_level = getattr(self, '_privacy_level', None)
                yield obj
        return _generator()


class UserProfileManager(models.Manager):
    """Custom Manager for UserProfile."""

    use_for_related_fields = True

    def get_query_set(self):
        return UserProfileQuerySet(self.model)

    def __getattr__(self, name):
        return getattr(self.get_query_set(), name)


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
    _privacy_fields = {'photo': None,
                       'full_name': '',
                       'ircname': '',
                       'email': '',
                       'website': '',
                       'bio': '',
                       'city': '',
                       'region': '',
                       'country': '',
                       'groups': Group.objects.none(),
                       'skills': Skill.objects.none(),
                       'languages': Language.objects.none(),
                       'vouched_by': None,
                       'date_mozillian': None,
                       'timezone': ''}
    _privacy_level = None

    privacy_photo = models.PositiveIntegerField(default=MOZILLIANS,
                                                choices=PRIVACY_CHOICES)
    privacy_full_name = models.PositiveIntegerField(default=MOZILLIANS,
                                                    choices=PRIVACY_CHOICES)
    privacy_ircname = models.PositiveIntegerField(default=MOZILLIANS,
                                                  choices=PRIVACY_CHOICES)
    privacy_email = models.PositiveIntegerField(default=MOZILLIANS,
                                                choices=PRIVACY_CHOICES)
    privacy_website = models.PositiveIntegerField(default=MOZILLIANS,
                                                  choices=PRIVACY_CHOICES)
    privacy_bio = models.PositiveIntegerField(default=MOZILLIANS,
                                              choices=PRIVACY_CHOICES)
    privacy_city = models.PositiveIntegerField(default=MOZILLIANS,
                                               choices=PRIVACY_CHOICES)
    privacy_region = models.PositiveIntegerField(default=MOZILLIANS,
                                                 choices=PRIVACY_CHOICES)
    privacy_country = models.PositiveIntegerField(default=MOZILLIANS,
                                                  choices=PRIVACY_CHOICES)
    privacy_groups = models.PositiveIntegerField(default=MOZILLIANS,
                                                 choices=PRIVACY_CHOICES)
    privacy_skills = models.PositiveIntegerField(default=MOZILLIANS,
                                                 choices=PRIVACY_CHOICES)
    privacy_languages = models.PositiveIntegerField(default=MOZILLIANS,
                                                    choices=PRIVACY_CHOICES)
    privacy_vouched_by = models.PositiveIntegerField(default=MOZILLIANS,
                                                     choices=PRIVACY_CHOICES)
    privacy_date_mozillian = models.PositiveIntegerField(
        default=MOZILLIANS, choices=PRIVACY_CHOICES)
    privacy_timezone = models.PositiveIntegerField(
        default=MOZILLIANS, choices=PRIVACY_CHOICES)

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
    timezone = models.CharField(max_length=100, blank=True, default='')

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
    def email(self):
        """Privacy aware email property."""
        if self._privacy_level and self.privacy_email < self._privacy_level:
            return self._privacy_fields['email']
        return self.user.email

    @property
    def display_name(self):
        return self.full_name

    @property
    def level(self):
        """Return user privacy clearance."""
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

            if not getattr(g, 'system', False):
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
        if not self.photo and self.privacy_photo >= self._privacy_level:
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
        elif staff in self.groups.all():
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
        index_objects.delay(sender, [instance.id], public=False)
        if instance.is_public_indexable:
            index_objects.delay(sender, [instance.id], public_index=True)
        else:
            unindex_objects(UserProfile, [instance.id], public_index=True)


@receiver(dbsignals.post_delete, sender=UserProfile,
          dispatch_uid='remove_from_search_index_sig')
def remove_from_search_index(sender, instance, **kwargs):
    unindex_objects(UserProfile, [instance.id], public_index=False)
    unindex_objects(UserProfile, [instance.id], public_index=True)


class UsernameBlacklist(models.Model):
    value = models.CharField(max_length=30, unique=True)
    is_regex = models.BooleanField(default=False)

    def __unicode__(self):
        return self.value

    class Meta:
        ordering = ['value']
