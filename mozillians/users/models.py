import logging
import os
import uuid
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models
from django.db.models import signals as dbsignals, ManyToManyField
from django.dispatch import receiver
from django.utils.encoding import iri_to_uri
from django.utils.http import urlquote
from django.template.loader import get_template


import basket
from elasticutils.contrib.django import S, get_es
from elasticutils.contrib.django.models import SearchMixin
from funfactory.urlresolvers import reverse
from product_details import product_details
from pytz import common_timezones
from sorl.thumbnail import ImageField, get_thumbnail
from south.modelsinspector import add_introspection_rules
from tower import ugettext as _, ugettext_lazy as _lazy
from funfactory import utils

from mozillians.common.helpers import gravatar
from mozillians.common.helpers import offset_of_timezone
from mozillians.groups.models import (Group, GroupAlias, GroupMembership,
                                      Skill, SkillAlias)
from mozillians.phonebook.helpers import langcode_to_name
from mozillians.phonebook.validators import (validate_email, validate_twitter,
                                             validate_website, validate_username_not_url,
                                             validate_phone_number)
from mozillians.users import get_languages_for_locale
from mozillians.users.managers import (EMPLOYEES,
                                       MOZILLIANS, PRIVACY_CHOICES, PRIVILEGED,
                                       PUBLIC, PUBLIC_INDEXABLE_FIELDS,
                                       UserProfileManager)
from mozillians.users.tasks import (index_objects, remove_from_basket_task,
                                    update_basket_task, unindex_objects)


COUNTRIES = product_details.get_regions('en-US')
AVATAR_SIZE = (300, 300)
logger = logging.getLogger(__name__)


def _calculate_photo_filename(instance, filename):
    """Generate a unique filename for uploaded photo."""
    return os.path.join(settings.USER_AVATAR_DIR, str(uuid.uuid4()) + '.jpg')


class PrivacyField(models.PositiveSmallIntegerField):

    def __init__(self, *args, **kwargs):
        myargs = {'default': MOZILLIANS,
                  'choices': PRIVACY_CHOICES}
        myargs.update(kwargs)
        super(PrivacyField, self).__init__(*args, **myargs)
add_introspection_rules([], ['^mozillians\.users\.models\.PrivacyField'])


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
    _privacy_level = None

    privacy_photo = PrivacyField()
    privacy_full_name = PrivacyField()
    privacy_ircname = PrivacyField()
    privacy_email = PrivacyField()
    privacy_bio = PrivacyField()
    privacy_geo_city = PrivacyField()
    privacy_geo_region = PrivacyField()
    privacy_geo_country = PrivacyField()
    privacy_groups = PrivacyField()
    privacy_skills = PrivacyField()
    privacy_languages = PrivacyField()
    privacy_date_mozillian = PrivacyField()
    privacy_timezone = PrivacyField()
    privacy_tshirt = PrivacyField(choices=((PRIVILEGED, _lazy(u'Privileged')),),
                                  default=PRIVILEGED)
    privacy_title = PrivacyField()
    privacy_story_link = PrivacyField()

    CACHED_PRIVACY_FIELDS = None

    class Meta:
        abstract = True

    @classmethod
    def clear_privacy_fields_cache(cls):
        """
        Clear any caching of the privacy fields.
        (This is only used in testing.)
        """
        cls.CACHED_PRIVACY_FIELDS = None

    @classmethod
    def privacy_fields(cls):
        """
        Return a dictionary whose keys are the names of the fields in this
        model that are privacy-controlled, and whose values are the default
        values to use for those fields when the user is not privileged to
        view their actual value.
        """
        # Cache on the class object
        if cls.CACHED_PRIVACY_FIELDS is None:
            privacy_fields = {}
            field_names = cls._meta.get_all_field_names()
            for name in field_names:
                if name.startswith('privacy_') or not 'privacy_%s' % name in field_names:
                    # skip privacy fields and uncontrolled fields
                    continue
                field = cls._meta.get_field(name)
                # Okay, this is a field that is privacy-controlled
                # Figure out a good default value for it (to show to users
                # who aren't privileged to see the actual value)
                if isinstance(field, ManyToManyField):
                    default = field.related.parent_model.objects.none()
                else:
                    default = field.get_default()
                privacy_fields[name] = default
            # HACK: There's not really an email field on UserProfile, but it's faked with a property
            privacy_fields['email'] = u''

            cls.CACHED_PRIVACY_FIELDS = privacy_fields
        return cls.CACHED_PRIVACY_FIELDS


class UserProfile(UserProfilePrivacyModel, SearchMixin):
    objects = UserProfileManager()

    user = models.OneToOneField(User)
    full_name = models.CharField(max_length=255, default='', blank=False,
                                 verbose_name=_lazy(u'Full Name'))
    is_vouched = models.BooleanField(
        default=False,
        help_text='You can edit vouched status by editing invidual vouches')
    can_vouch = models.BooleanField(
        default=False,
        help_text='You can edit can_vouch status by editing invidual vouches')
    last_updated = models.DateTimeField(auto_now=True, default=datetime.now)
    groups = models.ManyToManyField(Group, blank=True, related_name='members',
                                    through=GroupMembership)
    skills = models.ManyToManyField(Skill, blank=True, related_name='members')
    bio = models.TextField(verbose_name=_lazy(u'Bio'), default='', blank=True)
    photo = ImageField(default='', blank=True,
                       upload_to=_calculate_photo_filename)
    ircname = models.CharField(max_length=63,
                               verbose_name=_lazy(u'IRC Nickname'),
                               default='', blank=True)

    # legacy geo data
    country = models.CharField(max_length=50, default='',
                               choices=COUNTRIES.items(),
                               verbose_name=_lazy(u'Country'))
    region = models.CharField(max_length=255, default='', blank=True,
                              verbose_name=_lazy(u'Province/State'))
    city = models.CharField(max_length=255, default='', blank=True,
                            verbose_name=_lazy(u'City'))

    # validated geo data (validated that it's valid geo data, not that the
    # mozillian is there :-) )
    geo_country = models.ForeignKey('geo.Country', blank=True, null=True, on_delete=models.SET_NULL)
    geo_region = models.ForeignKey('geo.Region', blank=True, null=True, on_delete=models.SET_NULL)
    geo_city = models.ForeignKey('geo.City', blank=True, null=True, on_delete=models.SET_NULL)
    lat = models.FloatField(_lazy(u'Latitude'), blank=True, null=True)
    lng = models.FloatField(_lazy(u'Longitude'), blank=True, null=True)

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
            (1, _lazy(u'Fitted Small')), (2, _lazy(u'Fitted Medium')),
            (3, _lazy(u'Fitted Large')), (4, _lazy(u'Fitted X-Large')),
            (5, _lazy(u'Fitted XX-Large')), (6, _lazy(u'Fitted XXX-Large')),
            (7, _lazy(u'Straight-cut Small')), (8, _lazy(u'Straight-cut Medium')),
            (9, _lazy(u'Straight-cut Large')), (10, _lazy(u'Straight-cut X-Large')),
            (11, _lazy(u'Straight-cut XX-Large')), (12, _lazy(u'Straight-cut XXX-Large'))
        ))
    title = models.CharField(_lazy(u'What do you do for Mozilla?'),
                             max_length=70, blank=True, default='')

    story_link = models.URLField(
        _lazy(u'Link to your contribution story'),
        help_text=_lazy(u'If you have created something public that '
                        u'tells the story of how you came to be a '
                        u'Mozillian, specify that link here.'),
        max_length=1024, blank=True, default='')

    class Meta:
        db_table = 'profile'
        ordering = ['full_name']

    def __getattribute__(self, attrname):
        """Special privacy aware __getattribute__ method.

        This method returns the real value of the attribute of object,
        if the privacy_level of the attribute is at least as large as
        the _privacy_level attribute.

        Otherwise it returns a default privacy respecting value for
        the attribute, as defined in the privacy_fields dictionary.

        special_functions provides methods that privacy safe their
        respective properties, where the privacy modifications are
        more complex.
        """
        _getattr = (lambda x: super(UserProfile, self).__getattribute__(x))
        privacy_fields = UserProfile.privacy_fields()
        privacy_level = _getattr('_privacy_level')
        special_functions = {'vouches_made': '_vouches_made',
                             'vouches_received': '_vouches_received'}

        if attrname in special_functions and privacy_level:
            return _getattr(special_functions[attrname])

        if not privacy_level:
            return _getattr(attrname)

        if attrname not in privacy_fields:
            return _getattr(attrname)

        field_privacy = _getattr('privacy_%s' % attrname)
        if field_privacy < privacy_level:
            return privacy_fields.get(attrname)

        return _getattr(attrname)

    def _vouches(self, type):
        _getattr = (lambda x: super(UserProfile, self).__getattribute__(x))
        privacy_level = _getattr('_privacy_level')

        vouch_ids = []
        for vouch in _getattr(type).all():
            vouch.vouchee.set_instance_privacy_level(privacy_level)
            for field in UserProfile.privacy_fields():
                if getattr(vouch.vouchee, 'privacy_%s' % field, 0) >= privacy_level:
                    vouch_ids.append(vouch.id)
        vouches_made = _getattr(type).filter(pk__in=vouch_ids)

        return vouches_made

    @property
    def _vouches_made(self):
        return self._vouches('vouches_made')

    @property
    def _vouches_received(self):
        return self._vouches('vouches_received')

    @classmethod
    def extract_document(cls, obj_id, obj=None):
        """Method used by elasticutils."""
        if obj is None:
            obj = cls.objects.get(pk=obj_id)
        d = {}

        attrs = ('id', 'is_vouched', 'ircname',
                 'allows_mozilla_sites', 'allows_community_sites')
        for a in attrs:
            data = getattr(obj, a)
            if isinstance(data, basestring):
                data = data.lower()
            d.update({a: data})

        d['country'] = [obj.geo_country.name, obj.geo_country.code] if obj.geo_country else None
        d['region'] = obj.geo_region.name if obj.geo_region else None
        d['city'] = obj.geo_city.name if obj.geo_city else None

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

        for attribute in ['groups', 'skills']:
            groups = []
            for g in getattr(obj, attribute).all():
                groups.extend(g.aliases.values_list('name', flat=True))
            d[attribute] = groups
        # Add to search index language code, language name in English
        # native lanugage name.
        languages = []
        for code in obj.languages.values_list('code', flat=True):
            languages.append(code)
            languages.append(langcode_to_name(code, 'en_US').lower())
            languages.append(langcode_to_name(code, code).lower())
        d['languages'] = list(set(languages))
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
        accounts_query = self.externalaccount_set.exclude(type=ExternalAccount.TYPE_WEBSITE)
        if self._privacy_level:
            accounts_query = accounts_query.filter(privacy__gte=self._privacy_level)
        return accounts_query

    @property
    def websites(self):
        websites_query = self.externalaccount_set.filter(type=ExternalAccount.TYPE_WEBSITE)
        if self._privacy_level:
            websites_query = websites_query.filter(privacy__gte=self._privacy_level)
        return websites_query

    @property
    def email(self):
        """Privacy aware email property."""
        if self._privacy_level and self.privacy_email < self._privacy_level:
            return type(self).privacy_fields()['email']
        return self.user.email

    @property
    def display_name(self):
        return self.full_name

    @property
    def privacy_level(self):
        """Return user privacy clearance."""
        if (self.user.groups.filter(name='Managers').exists() or self.user.is_superuser):
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
        for field in type(self).privacy_fields():
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

    @property
    def is_manager(self):
        return self.user.is_superuser or self.user.groups.filter(name='Managers').exists()

    @property
    def languages(self):
        """Return user languages based on privacy settings."""
        if self._privacy_level > self.privacy_languages:
            return self.language_set.none()
        return self.language_set.all()

    @property
    def vouched_by(self):
        """Return the first userprofile who vouched for this userprofile."""
        privacy_level = self._privacy_level
        voucher = (UserProfile.objects.filter(vouches_made__vouchee=self)
                                      .order_by('vouches_made__date'))

        if voucher:
            voucher = voucher[0]
            if privacy_level:
                voucher.set_instance_privacy_level(privacy_level)
                for field in UserProfile.privacy_fields():
                    if getattr(voucher, 'privacy_%s' % field) >= privacy_level:
                        return voucher
                return None
            return voucher

        return None

    @property
    def date_vouched(self):
        """ Return the date of the first vouch, if available."""
        vouches = self.vouches_received.all().order_by('date')[:1]
        if vouches:
            return vouches[0].date
        return None

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
        for field in type(self).privacy_fields():
            setattr(self, 'privacy_%s' % field, level)
        if save:
            self.save()

    def set_membership(self, model, membership_list):
        """Alters membership to Groups and Skills."""
        if model is Group:
            m2mfield = self.groups
            alias_model = GroupAlias
        elif model is Skill:
            m2mfield = self.skills
            alias_model = SkillAlias

        # Remove any visible groups that weren't supplied in this list.
        if model is Group:
            GroupMembership.objects.filter(userprofile=self, group__visible=True)\
                .exclude(group__name__in=membership_list).delete()
        else:
            m2mfield.remove(*[g for g in m2mfield.all()
                              if g.name not in membership_list
                              and g.is_visible])

        # Add/create the rest of the groups
        groups_to_add = []
        for g in membership_list:
            if alias_model.objects.filter(name=g).exists():
                group = alias_model.objects.get(name=g).alias
            else:
                group = model.objects.create(name=g)

            if group.is_visible:
                groups_to_add.append(group)

        if model is Group:
            for group in groups_to_add:
                group.add_member(self)
        else:
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

    def is_vouchable(self, voucher):
        """Check whether self can receive a vouch from voucher."""
        # If there's a voucher, they must be able to vouch.
        if voucher and not voucher.can_vouch:
            return False

        # Maximum VOUCH_COUNT_LIMIT vouches per account, no matter what.
        if self.vouches_received.all().count() >= settings.VOUCH_COUNT_LIMIT:
            return False

        # If you've already vouched this account, you cannot do it again, unless
        # this account has a legacy vouch from you.
        vouch_query = self.vouches_received.filter(voucher=voucher)
        if voucher and vouch_query.exists():
            if vouch_query.filter(description='').exists():
                return True
            return False

        return True

    def vouch(self, vouched_by, description='', autovouch=False):
        if not self.is_vouchable(vouched_by):
            return

        now = datetime.now()
        # Update a legacy vouch, if exists, by re-vouching
        # https://bugzilla.mozilla.org/show_bug.cgi?id=1033306
        query = self.vouches_received.filter(voucher=vouched_by)
        if query.filter(description='').exists():
            # If there isn't a date, provide one
            vouch = query[0]
            vouch.description = description
            if not vouch.date:
                vouch.date = now
            vouch.save()
        else:
            vouch = self.vouches_received.create(
                voucher=vouched_by,
                date=now,
                description=description,
                autovouch=autovouch
            )

        self._email_now_vouched(vouched_by)
        return vouch

    def auto_vouch(self):
        """Auto vouch mozilla.com users."""
        email = self.user.email

        if any(email.endswith('@' + x) for x in settings.AUTO_VOUCH_DOMAINS):
            if not self.vouches_received.filter(
                    description=settings.AUTO_VOUCH_REASON, autovouch=True).exists():
                self.vouch(None, settings.AUTO_VOUCH_REASON, autovouch=True)

    def _email_now_vouched(self, vouched_by):
        """Email this user, letting them know they are now vouched."""
        name = None
        profile_link = None
        if vouched_by:
            name = vouched_by.full_name
            profile_link = utils.absolutify(vouched_by.get_absolute_url())

        number_of_vouches = self.vouches_received.all().count()
        template = get_template('phonebook/emails/vouch_confirmation_email.txt')
        message = template.render({
            'voucher_name': name,
            'voucher_profile_url': profile_link,
            'functional_areas_url': utils.absolutify(reverse('groups:index_functional_areas')),
            'groups_url': utils.absolutify(reverse('groups:index_groups')),
            'first_vouch': number_of_vouches == 1,
            'can_vouch_threshold': number_of_vouches == settings.CAN_VOUCH_THRESHOLD,
        })
        subject = _(u'You are now vouched on Mozillians.org')
        filtered_message = message.replace('&#34;', '"').replace('&#39;', "'")
        send_mail(subject, filtered_message, settings.FROM_NOREPLY,
                  [self.user.email])

    def lookup_basket_token(self):
        """
        Query Basket for this user's token.  If Basket doesn't find the user,
        returns None. If Basket does find the token, returns it. Otherwise,
        there must have been some error from the network or basket, and this
        method just lets that exception propagate so the caller can decide how
        best to handle it.

        (Does not update the token field on the UserProfile.)
        """
        try:
            result = basket.lookup_user(email=self.user.email)
        except basket.BasketException as exception:
            if exception.code == basket.errors.BASKET_UNKNOWN_EMAIL:
                return None
            raise
        return result['token']

    def get_annotated_groups(self):
        """
        Return a list of all the groups the user is a member of or pending
        membership. The groups pending membership will have a .pending attribute
        set to True, others will have it set False.
        """
        groups = []
        # Query this way so we only get the groups that the privacy controls allow the
        # current user to see. We have to force evaluation of this query first, otherwise
        # Django combines the whole thing into one query and loses the privacy control.
        user_group_ids = list(self.groups.values_list('id', flat=True))
        for membership in self.groupmembership_set.filter(group_id__in=user_group_ids):
            group = membership.group
            group.pending = (membership.status == GroupMembership.PENDING)
            groups.append(group)
        return groups

    def timezone_offset(self):
        """
        Return minutes the user's timezone is offset from UTC.  E.g. if user is
        4 hours behind UTC, returns -240.
        If user has not set a timezone, returns None (not 0).
        """
        if self.timezone:
            return offset_of_timezone(self.timezone)

    def save(self, *args, **kwargs):
        self._privacy_level = None
        super(UserProfile, self).save(*args, **kwargs)
        # Auto_vouch follows the first save, because you can't
        # create foreign keys without a database id.
        self.auto_vouch()

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

    def reverse_geocode(self):
        """
        Use the user's lat and lng to set their city, region, and country.
        Does not save the profile.
        """
        if self.lat is None or self.lng is None:
            return

        from mozillians.geo.models import Country
        from mozillians.geo.lookup import reverse_geocode, GeoLookupException
        try:
            result = reverse_geocode(self.lat, self.lng)
        except GeoLookupException:
            if self.geo_country:
                # If self.geo_country is already set, just give up.
                pass
            else:
                # No country set, we need to at least set the placeholder one.
                self.geo_country = Country.objects.get(mapbox_id='geo_error')
                self.geo_region = None
                self.geo_city = None
        else:
            if result:
                country, region, city = result
                self.geo_country = country
                self.geo_region = region
                self.geo_city = city
            else:
                logger.error('Got back NONE from reverse_geocode on %s, %s' % (self.lng, self.lat))


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


@receiver(dbsignals.pre_delete, sender=UserProfile,
          dispatch_uid='remove_from_basket_sig')
def remove_from_basket(sender, instance, **kwargs):
    remove_from_basket_task.delay(instance.email, instance.basket_token)


@receiver(dbsignals.post_delete, sender=UserProfile,
          dispatch_uid='delete_user_obj_sig')
def delete_user_obj_sig(sender, instance, **kwargs):
    if instance.user:
        instance.user.delete()


class Vouch(models.Model):
    vouchee = models.ForeignKey(UserProfile, related_name='vouches_received')
    voucher = models.ForeignKey(UserProfile, related_name='vouches_made',
                                null=True, default=None, blank=True,
                                on_delete=models.SET_NULL)
    description = models.TextField(max_length=500, verbose_name=_lazy(u'Reason for Vouching'),
                                   default='')
    autovouch = models.BooleanField(default=False)

    # The back-end can set date null, for migration purposes, but forms cannot.
    date = models.DateTimeField(null=True, default=None)

    class Meta:
        verbose_name_plural = 'vouches'
        unique_together = ('vouchee', 'voucher')
        ordering = ['-date']

    def __unicode__(self):
        return u'{0} vouched by {1}'.format(self.vouchee, self.voucher)


@receiver(dbsignals.post_delete, sender=Vouch, dispatch_uid='update_vouch_flags_delete_sig')
@receiver(dbsignals.post_save, sender=Vouch, dispatch_uid='update_vouch_flags_save_sig')
def update_vouch_flags(sender, instance, **kwargs):
    if kwargs.get('raw'):
        return
    try:
        profile = instance.vouchee
    except UserProfile.DoesNotExist:
        # In this case we delete not only the vouches but the
        # UserProfile as well. Do nothing.
        return
    vouches = Vouch.objects.filter(vouchee=profile).count()
    profile.is_vouched = vouches > 0
    profile.can_vouch = vouches >= settings.CAN_VOUCH_THRESHOLD
    profile.save()


class UsernameBlacklist(models.Model):
    value = models.CharField(max_length=30, unique=True)
    is_regex = models.BooleanField(default=False)

    def __unicode__(self):
        return self.value

    class Meta:
        ordering = ['value']


class ExternalAccount(models.Model):
    # Constants for type field values.
    TYPE_AMO = 'AMO'
    TYPE_BMO = 'BMO'
    TYPE_GITHUB = 'GITHUB'
    TYPE_MDN = 'MDN'
    TYPE_SUMO = 'SUMO'
    TYPE_FACEBOOK = 'FACEBOOK'
    TYPE_TWITTER = 'TWITTER'
    TYPE_AIM = 'AIM'
    TYPE_GTALK = 'GTALK'
    TYPE_SKYPE = 'SKYPE'
    TYPE_YAHOO = 'YAHOO'
    TYPE_WEBSITE = 'WEBSITE'
    TYPE_BITBUCKET = 'BITBUCKET'
    TYPE_SLIDESHARE = 'SLIDESHARE'
    TYPE_WEBMAKER = 'WEBMAKER'
    TYPE_MOWIKI = 'MOZILLAWIKI'
    TYPE_REMO = 'REMO'
    TYPE_LINKEDIN = 'LINKEDIN'
    TYPE_JABBER = 'JABBER'
    TYPE_DISCOURSE = 'DISCOURSE'
    TYPE_LANYRD = 'LANYRD'
    TYPE_LANDLINE = 'Phone (Landline)'
    TYPE_MOBILE = 'Phone (Mobile)'

    # Account type field documentation:
    # name: The name of the service that this account belongs to. What
    #       users see
    # url: If the service features profile pages for its users, then
    #      this field should be a link to that profile page. User's
    #      identifier should be replaced by the special string
    #      {identifier}.
    # validator: Points to a function which will clean and validate
    #            user's entry. Function should return the cleaned
    #            data.
    ACCOUNT_TYPES = {
        TYPE_AMO: {'name': 'Mozilla Add-ons',
                   'url': 'https://addons.mozilla.org/user/{identifier}/',
                   'validator': validate_username_not_url},
        TYPE_BMO: {'name': 'Bugzilla (BMO)',
                   'url': 'https://bugzilla.mozilla.org/user_profile?login={identifier}',
                   'validator': validate_username_not_url},
        TYPE_GITHUB: {'name': 'GitHub',
                      'url': 'https://github.com/{identifier}',
                      'validator': validate_username_not_url},
        TYPE_BITBUCKET: {'name': 'Bitbucket',
                         'url': 'https://bitbucket.org/{identifier}',
                         'validator': validate_username_not_url},
        TYPE_MDN: {'name': 'MDN',
                   'url': 'https://developer.mozilla.org/profiles/{identifier}',
                   'validator': validate_username_not_url},
        TYPE_SUMO: {'name': 'Mozilla Support',
                    'url': 'https://support.mozilla.org/user/{identifier}',
                    'validator': validate_username_not_url},
        TYPE_FACEBOOK: {'name': 'Facebook',
                        'url': 'https://www.facebook.com/{identifier}',
                        'validator': validate_username_not_url},
        TYPE_TWITTER: {'name': 'Twitter',
                       'url': 'https://twitter.com/{identifier}',
                       'validator': validate_twitter},
        TYPE_AIM: {'name': 'AIM', 'url': ''},
        TYPE_GTALK: {'name': 'Google Talk',
                     'url': '',
                     'validator': validate_email},
        TYPE_SKYPE: {'name': 'Skype', 'url': ''},
        TYPE_SLIDESHARE: {'name': 'SlideShare',
                          'url': 'http://www.slideshare.net/{identifier}',
                          'validator': validate_username_not_url},
        TYPE_YAHOO: {'name': 'Yahoo! Messenger', 'url': ''},
        TYPE_WEBSITE: {'name': 'Website URL',
                       'url': '',
                       'validator': validate_website},
        TYPE_WEBMAKER: {'name': 'Mozilla Webmaker',
                        'url': 'https://{identifier}.makes.org',
                        'validator': validate_username_not_url},
        TYPE_MOWIKI: {'name': 'Mozilla Wiki', 'url': 'https://wiki.mozilla.org/User:{identifier}',
                      'validator': validate_username_not_url},
        TYPE_REMO: {'name': 'Mozilla Reps', 'url': 'https://reps.mozilla.org/u/{identifier}/',
                    'validator': validate_username_not_url},
        TYPE_LINKEDIN: {'name': 'LinkedIn',
                        'url': '',
                        'validator': validate_website},
        TYPE_JABBER: {'name': 'XMPP/Jabber',
                      'url': '',
                      'validator': validate_email},
        TYPE_DISCOURSE: {'name': 'Mozilla Discourse',
                         'url': 'https://discourse.mozilla-community.org/users/{identifier}',
                         'validator': validate_username_not_url},
        TYPE_LANYRD: {'name': 'Lanyrd',
                      'url': 'http://lanyrd.com/profile/{identifier}/',
                      'validator': validate_username_not_url},
        TYPE_LANDLINE: {'name': 'Phone (Landline)',
                        'url': '',
                        'validator': validate_phone_number},
        TYPE_MOBILE: {'name': 'Phone (Mobile)',
                      'url': '',
                      'validator': validate_phone_number},

    }

    user = models.ForeignKey(UserProfile)
    identifier = models.CharField(max_length=255, verbose_name=_lazy(u'Account Username'))
    type = models.CharField(
        max_length=30,
        choices=sorted([(k, v['name'])
                        for (k, v) in ACCOUNT_TYPES.iteritems()], key=lambda x: x[1]),
        verbose_name=_lazy(u'Account Type'))
    privacy = models.PositiveIntegerField(default=MOZILLIANS,
                                          choices=PRIVACY_CHOICES)

    class Meta:
        ordering = ['type']
        unique_together = ('identifier', 'type', 'user')

    def get_identifier_url(self):
        url = self.ACCOUNT_TYPES[self.type]['url'].format(identifier=urlquote(self.identifier))
        return iri_to_uri(url)

    def unique_error_message(self, model_class, unique_check):
        if model_class == type(self) and unique_check == ('identifier', 'type', 'user'):
            return _('You already have an account with this name and type.')
        else:
            return super(ExternalAccount, self).unique_error_message(model_class, unique_check)


class Language(models.Model):
    code = models.CharField(max_length=63, choices=get_languages_for_locale('en'))
    userprofile = models.ForeignKey(UserProfile)

    class Meta:
        ordering = ['code']
        unique_together = ('code', 'userprofile')

    def __unicode__(self):
        return self.code

    def unique_error_message(self, model_class, unique_check):
        if (model_class == type(self) and unique_check == ('code', 'userprofile')):
            return _('This language has already been selected.')
        return super(Language, self).unique_error_message(model_class, unique_check)
