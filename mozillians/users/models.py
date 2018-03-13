import logging
import os
import uuid
from itertools import chain

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.db import models
from django.db.models import Manager, ManyToManyField
from django.utils.encoding import iri_to_uri
from django.utils.http import urlquote
from django.utils.timezone import now
from django.template.loader import get_template

from product_details import product_details
from PIL import Image
from pytz import common_timezones
from sorl.thumbnail import ImageField, get_thumbnail
from django.utils.translation import ugettext as _, ugettext_lazy as _lazy

from mozillians.common import utils
from mozillians.common.templatetags.helpers import absolutify, gravatar
from mozillians.common.templatetags.helpers import offset_of_timezone
from mozillians.common.urlresolvers import reverse
from mozillians.groups.models import (Group, GroupAlias, GroupMembership, Invite,
                                      Skill, SkillAlias)
from mozillians.phonebook.validators import (validate_email, validate_twitter,
                                             validate_website, validate_username_not_url,
                                             validate_phone_number, validate_linkedin)
from mozillians.users import get_languages_for_locale
from mozillians.users.managers import (EMPLOYEES,
                                       MOZILLIANS, PRIVACY_CHOICES, PRIVACY_CHOICES_WITH_PRIVATE,
                                       PRIVATE, PUBLIC, PUBLIC_INDEXABLE_FIELDS,
                                       UserProfileQuerySet)
from mozillians.users.tasks import send_userprofile_to_cis


COUNTRIES = product_details.get_regions('en-US')
AVATAR_SIZE = (300, 300)
logger = logging.getLogger(__name__)
ProfileManager = Manager.from_queryset(UserProfileQuerySet)


def _calculate_photo_filename(instance, filename):
    """Generate a unique filename for uploaded photo."""
    return os.path.join(settings.USER_AVATAR_DIR, str(uuid.uuid4()) + '.jpg')


class PrivacyField(models.PositiveSmallIntegerField):

    def __init__(self, *args, **kwargs):
        myargs = {'default': MOZILLIANS,
                  'choices': PRIVACY_CHOICES}
        myargs.update(kwargs)
        super(PrivacyField, self).__init__(*args, **myargs)


class UserProfilePrivacyModel(models.Model):
    _privacy_level = None

    privacy_photo = PrivacyField()
    privacy_full_name = PrivacyField()
    privacy_full_name_local = PrivacyField()
    privacy_ircname = PrivacyField()
    privacy_email = PrivacyField(choices=PRIVACY_CHOICES_WITH_PRIVATE,
                                 default=MOZILLIANS)
    privacy_bio = PrivacyField()
    privacy_geo_city = PrivacyField()
    privacy_geo_region = PrivacyField()
    privacy_geo_country = PrivacyField()
    privacy_city = PrivacyField()
    privacy_region = PrivacyField()
    privacy_country = PrivacyField()
    privacy_groups = PrivacyField()
    privacy_skills = PrivacyField()
    privacy_languages = PrivacyField()
    privacy_date_mozillian = PrivacyField()
    privacy_timezone = PrivacyField()
    privacy_tshirt = PrivacyField(choices=((PRIVATE, _lazy(u'Private')),),
                                  default=PRIVATE)
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

        Note: should be only used through UserProfile . We should
        fix this.

        """
        # Cache on the class object
        if cls.CACHED_PRIVACY_FIELDS is None:
            privacy_fields = {}
            field_names = list(set(chain.from_iterable(
                (field.name, field.attname) if hasattr(field, 'attname') else
                (field.name,) for field in cls._meta.get_fields()
                if not (field.many_to_one and field.related_model is None)
            )))
            for name in field_names:
                if name.startswith('privacy_') or not 'privacy_%s' % name in field_names:
                    # skip privacy fields and uncontrolled fields
                    continue
                field = cls._meta.get_field(name)
                # Okay, this is a field that is privacy-controlled
                # Figure out a good default value for it (to show to users
                # who aren't privileged to see the actual value)
                if isinstance(field, ManyToManyField):
                    default = field.remote_field.model.objects.none()
                else:
                    default = field.get_default()
                privacy_fields[name] = default
            # HACK: There's not really an email field on UserProfile,
            # but it's faked with a property
            privacy_fields['email'] = u''

            cls.CACHED_PRIVACY_FIELDS = privacy_fields
        return cls.CACHED_PRIVACY_FIELDS


class UserProfile(UserProfilePrivacyModel):
    REFERRAL_SOURCE_CHOICES = (
        ('direct', 'Mozillians'),
        ('contribute', 'Get Involved'),
    )

    objects = ProfileManager()

    user = models.OneToOneField(User)
    full_name = models.CharField(max_length=255, default='', blank=False,
                                 verbose_name=_lazy(u'Full Name'))
    full_name_local = models.CharField(max_length=255, blank=True, default='',
                                       verbose_name=_lazy(u'Name in local language'))
    is_vouched = models.BooleanField(
        default=False,
        help_text='You can edit vouched status by editing invidual vouches')
    can_vouch = models.BooleanField(
        default=False,
        help_text='You can edit can_vouch status by editing invidual vouches')
    last_updated = models.DateTimeField(auto_now=True)
    groups = models.ManyToManyField(Group, blank=True, related_name='members',
                                    through=GroupMembership)
    skills = models.ManyToManyField(Skill, blank=True, related_name='members')
    bio = models.TextField(verbose_name=_lazy(u'Bio'), default='', blank=True)
    photo = ImageField(default='', blank=True, upload_to=_calculate_photo_filename)
    ircname = models.CharField(max_length=63, verbose_name=_lazy(u'IRC Nickname'),
                               default='', blank=True)

    # validated geo data (validated that it's valid geo data, not that the
    # mozillian is there :-) )
    geo_country = models.ForeignKey('geo.Country', blank=True, null=True,
                                    on_delete=models.SET_NULL)
    geo_region = models.ForeignKey('geo.Region', blank=True, null=True, on_delete=models.SET_NULL)
    geo_city = models.ForeignKey('geo.City', blank=True, null=True, on_delete=models.SET_NULL)
    lat = models.FloatField(_lazy(u'Latitude'), blank=True, null=True)
    lng = models.FloatField(_lazy(u'Longitude'), blank=True, null=True)

    # django-cities-light fields
    city = models.ForeignKey('cities_light.City', blank=True, null=True,
                             on_delete=models.SET_NULL)
    region = models.ForeignKey('cities_light.Region', blank=True, null=True,
                               on_delete=models.SET_NULL)
    country = models.ForeignKey('cities_light.Country', blank=True, null=True,
                                on_delete=models.SET_NULL)

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
    referral_source = models.CharField(max_length=32,
                                       choices=REFERRAL_SOURCE_CHOICES,
                                       default='direct')

    def __unicode__(self):
        """Return this user's name when their profile is called."""
        return self.display_name

    def get_absolute_url(self):
        return reverse('phonebook:profile_view', args=[self.user.username])

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
        special_functions = {
            'accounts': '_accounts',
            'alternate_emails': '_alternate_emails',
            'email': '_primary_email',
            'is_public_indexable': '_is_public_indexable',
            'languages': '_languages',
            'vouches_made': '_vouches_made',
            'vouches_received': '_vouches_received',
            'vouched_by': '_vouched_by',
            'websites': '_websites',
            'identity_profiles': '_identity_profiles'
        }

        if attrname in special_functions:
            return _getattr(special_functions[attrname])

        if not privacy_level or attrname not in privacy_fields:
            return _getattr(attrname)

        field_privacy = _getattr('privacy_%s' % attrname)
        if field_privacy < privacy_level:
            return privacy_fields.get(attrname)

        return _getattr(attrname)

    def _filter_accounts_privacy(self, accounts):
        if self._privacy_level:
            return accounts.filter(privacy__gte=self._privacy_level)
        return accounts

    @property
    def _accounts(self):
        _getattr = (lambda x: super(UserProfile, self).__getattribute__(x))
        excluded_types = [ExternalAccount.TYPE_WEBSITE, ExternalAccount.TYPE_EMAIL]
        accounts = _getattr('externalaccount_set').exclude(type__in=excluded_types)
        return self._filter_accounts_privacy(accounts)

    @property
    def _alternate_emails(self):
        _getattr = (lambda x: super(UserProfile, self).__getattribute__(x))
        accounts = _getattr('externalaccount_set').filter(type=ExternalAccount.TYPE_EMAIL)
        return self._filter_accounts_privacy(accounts)

    @property
    def _api_alternate_emails(self):
        """
        Helper private property that creates a compatibility layer
        for API results in alternate emails. Combines both IdpProfile
        and ExternalAccount objects. In conflicts/duplicates it returns
        the minimum privacy level defined.
        """
        legacy_emails_qs = self._alternate_emails
        idp_qs = self._identity_profiles

        e_exclude = [e.id for e in legacy_emails_qs if
                     idp_qs.filter(email=e.identifier, privacy__gte=e.privacy).exists()]
        legacy_emails_qs = legacy_emails_qs.exclude(id__in=e_exclude)

        idp_exclude = [i.id for i in idp_qs if
                       legacy_emails_qs.filter(identifier=i.email,
                                               privacy__gte=i.privacy).exists()]
        idp_qs = idp_qs.exclude(id__in=idp_exclude)

        return chain(legacy_emails_qs, idp_qs)

    @property
    def _identity_profiles(self):
        _getattr = (lambda x: super(UserProfile, self).__getattribute__(x))
        accounts = _getattr('idp_profiles').all()
        return self._filter_accounts_privacy(accounts)

    @property
    def _is_public_indexable(self):
        for field in PUBLIC_INDEXABLE_FIELDS:
            if getattr(self, field, None) and getattr(self, 'privacy_%s' % field, None) == PUBLIC:
                return True
        return False

    @property
    def _languages(self):
        _getattr = (lambda x: super(UserProfile, self).__getattribute__(x))
        if self._privacy_level > _getattr('privacy_languages'):
            return _getattr('language_set').none()
        return _getattr('language_set').all()

    @property
    def _primary_email(self):
        _getattr = (lambda x: super(UserProfile, self).__getattribute__(x))

        privacy_fields = UserProfile.privacy_fields()

        if self._privacy_level:
            # Try IDP contact first
            if self.idp_profiles.exists():
                contact_ids = self.identity_profiles.filter(primary_contact_identity=True)
                if contact_ids.exists():
                    return contact_ids[0].email
                return ''

            # Fallback to user.email
            if _getattr('privacy_email') < self._privacy_level:
                return privacy_fields['email']

        # In case we don't have a privacy aware attribute access
        if self.idp_profiles.filter(primary_contact_identity=True).exists():
            return self.idp_profiles.filter(primary_contact_identity=True)[0].email
        return _getattr('user').email

    @property
    def _vouched_by(self):
        privacy_level = self._privacy_level
        voucher = (UserProfile.objects.filter(vouches_made__vouchee=self)
                   .order_by('vouches_made__date'))

        if voucher.exists():
            voucher = voucher[0]
            if privacy_level:
                voucher.set_instance_privacy_level(privacy_level)
                for field in UserProfile.privacy_fields():
                    if getattr(voucher, 'privacy_%s' % field) >= privacy_level:
                        return voucher
                return None
            return voucher

        return None

    def _vouches(self, type):
        _getattr = (lambda x: super(UserProfile, self).__getattribute__(x))

        vouch_ids = []
        for vouch in _getattr(type).all():
            vouch.vouchee.set_instance_privacy_level(self._privacy_level)
            for field in UserProfile.privacy_fields():
                if getattr(vouch.vouchee, 'privacy_%s' % field, 0) >= self._privacy_level:
                    vouch_ids.append(vouch.id)
        vouches = _getattr(type).filter(pk__in=vouch_ids)

        return vouches

    @property
    def _vouches_made(self):
        _getattr = (lambda x: super(UserProfile, self).__getattribute__(x))
        if self._privacy_level:
            return self._vouches('vouches_made')
        return _getattr('vouches_made')

    @property
    def _vouches_received(self):
        _getattr = (lambda x: super(UserProfile, self).__getattribute__(x))
        if self._privacy_level:
            return self._vouches('vouches_received')
        return _getattr('vouches_received')

    @property
    def _websites(self):
        _getattr = (lambda x: super(UserProfile, self).__getattribute__(x))
        accounts = _getattr('externalaccount_set').filter(type=ExternalAccount.TYPE_WEBSITE)
        return self._filter_accounts_privacy(accounts)

    @property
    def display_name(self):
        return self.full_name

    @property
    def privacy_level(self):
        """Return user privacy clearance."""
        if (self.user.groups.filter(name='Managers').exists() or self.user.is_superuser):
            return PRIVATE
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
        # TODO needs update

        for field in type(self).privacy_fields():
            if getattr(self, 'privacy_%s' % field, None) == PUBLIC:
                return True
        return False

    @property
    def is_manager(self):
        return self.user.is_superuser or self.user.groups.filter(name='Managers').exists()

    @property
    def is_nda(self):
        query = {
            'userprofile__pk': self.pk,
            'group__name': settings.NDA_GROUP,
            'status': GroupMembership.MEMBER
        }
        return GroupMembership.objects.filter(**query).exists() or self.user.is_superuser

    @property
    def date_vouched(self):
        """ Return the date of the first vouch, if available."""
        vouches = self.vouches_received.all().order_by('date')[:1]
        if vouches:
            return vouches[0].date
        return None

    @property
    def can_create_access_groups(self):
        """Check if a user can provision access groups.

        An access group is provisioned if a user holds an email in the AUTO_VOUCH_DOMAINS
        and has an LDAP IdpProfile or the user has a superuser account.
        """
        emails = set(
            [idp.email for idp in
             IdpProfile.objects.filter(profile=self, type=IdpProfile.PROVIDER_LDAP)
             if idp.email.split('@')[1] in settings.AUTO_VOUCH_DOMAINS]
        )
        if self.user.is_superuser or emails:
            return True
        return False

    def can_join_access_groups(self):
        """Check if a user can join access groups.

        A user can join an access group only if has an MFA account and
        belongs to the NDA group or is an employee.
        """
        if self.can_create_access_groups or self.is_nda:
            return True
        return False

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
            (GroupMembership.objects.filter(userprofile=self, group__visible=True)
                                    .exclude(group__name__in=membership_list).delete())
        else:
            m2mfield.remove(*[g for g in m2mfield.all()
                              if g.name not in membership_list and g.is_visible])

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

        if self.photo and default_storage.exists(self.photo):
            # Workaround for legacy images in RGBA model

            try:
                image_obj = Image.open(self.photo)
            except IOError:
                return get_thumbnail(settings.DEFAULT_AVATAR_PATH, geometry, **kwargs)

            if image_obj.mode == 'RGBA':
                new_fh = default_storage.open(self.photo.name, 'w')
                converted_image_obj = image_obj.convert('RGB')
                converted_image_obj.save(new_fh, 'JPEG')
                new_fh.close()

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
            return gravatar(self.email, size=geometry)

        photo_url = self.get_photo_thumbnail(geometry, **kwargs).url
        if photo_url.startswith('https://') or photo_url.startswith('http://'):
            return photo_url
        return absolutify(photo_url)

    def is_vouchable(self, voucher):
        """Check whether self can receive a vouch from voucher."""
        # If there's a voucher, they must be able to vouch.
        if voucher and not voucher.can_vouch:
            return False

        # Maximum VOUCH_COUNT_LIMIT vouches per account, no matter what.
        if self.vouches_received.all().count() >= settings.VOUCH_COUNT_LIMIT:
            return False

        # If you've already vouched this account, you cannot do it again
        vouch_query = self.vouches_received.filter(voucher=voucher)
        if voucher and vouch_query.exists():
            return False

        return True

    def vouch(self, vouched_by, description='', autovouch=False):
        if not self.is_vouchable(vouched_by):
            return

        vouch = self.vouches_received.create(
            voucher=vouched_by,
            date=now(),
            description=description,
            autovouch=autovouch
        )

        self._email_now_vouched(vouched_by, description)
        return vouch

    def auto_vouch(self):
        """Auto vouch mozilla.com users."""
        emails = [acc.identifier for acc in
                  ExternalAccount.objects.filter(user=self, type=ExternalAccount.TYPE_EMAIL)]
        emails.append(self.email)

        email_exists = any([email for email in emails
                            if email.split('@')[1] in settings.AUTO_VOUCH_DOMAINS])
        if email_exists and not self.vouches_received.filter(
                description=settings.AUTO_VOUCH_REASON, autovouch=True).exists():
            self.vouch(None, settings.AUTO_VOUCH_REASON, autovouch=True)

    def _email_now_vouched(self, vouched_by, description=''):
        """Email this user, letting them know they are now vouched."""
        name = None
        voucher_profile_link = None
        vouchee_profile_link = utils.absolutify(self.get_absolute_url())
        if vouched_by:
            name = vouched_by.full_name
            voucher_profile_link = utils.absolutify(vouched_by.get_absolute_url())

        number_of_vouches = self.vouches_received.all().count()
        template = get_template('phonebook/emails/vouch_confirmation_email.txt')
        message = template.render({
            'voucher_name': name,
            'voucher_profile_url': voucher_profile_link,
            'vouchee_profile_url': vouchee_profile_link,
            'vouch_description': description,
            'functional_areas_url': utils.absolutify(reverse('groups:index_functional_areas')),
            'groups_url': utils.absolutify(reverse('groups:index_groups')),
            'first_vouch': number_of_vouches == 1,
            'can_vouch_threshold': number_of_vouches == settings.CAN_VOUCH_THRESHOLD,
        })
        subject = _(u'You have been vouched on Mozillians.org')
        filtered_message = message.replace('&#34;', '"').replace('&#39;', "'")
        send_mail(subject, filtered_message, settings.FROM_NOREPLY,
                  [self.email])

    def _get_annotated_groups(self):
        # Query this way so we only get the groups that the privacy controls allow the
        # current user to see. We have to force evaluation of this query first, otherwise
        # Django combines the whole thing into one query and loses the privacy control.
        groups_manager = self.groups
        # checks to avoid AttributeError exception b/c self.groups may returns
        # EmptyQuerySet instead of the default manager due to privacy controls
        user_group_ids = []
        if hasattr(groups_manager, 'visible'):
            user_group_ids = groups_manager.visible().values_list('id', flat=True)

        return self.groupmembership_set.filter(group__id__in=user_group_ids)

    def get_annotated_tags(self):
        """
        Return a list of all the visible tags the user is a member of or pending
        membership. The groups pending membership will have a .pending attribute
        set to True, others will have it set False.
        """
        tags = self._get_annotated_groups().filter(group__is_access_group=False)
        annotated_tags = []
        for membership in tags:
            tag = membership.group
            tag.pending = (membership.status == GroupMembership.PENDING)
            tag.pending_terms = (membership.status == GroupMembership.PENDING_TERMS)
            annotated_tags.append(tag)
        return annotated_tags

    def get_annotated_access_groups(self):
        """
        Return a list of all the visible access groups the user is a member of or pending
        membership. The groups pending membership will have a .pending attribute
        set to True, others will have it set False. There is also an inviter attribute
        which displays the inviter of the user in the group.
        """
        access_groups = self._get_annotated_groups().filter(group__is_access_group=True)
        annotated_access_groups = []

        for membership in access_groups:
            group = membership.group
            group.pending = (membership.status == GroupMembership.PENDING)
            group.pending_terms = (membership.status == GroupMembership.PENDING_TERMS)

            try:
                invite = Invite.objects.get(group=membership.group, redeemer=self)
            except Invite.DoesNotExist:
                invite = None

            if invite:
                group.inviter = invite.inviter
            annotated_access_groups.append(group)

        return annotated_access_groups

    def get_cis_emails(self):
        """Prepares the entry for emails in the CIS format."""
        idp_profiles = self.idp_profiles.all()
        primary_idp = idp_profiles.filter(primary=True)
        emails = []
        primary_email = {
            'value': self.email,
            'verified': True,
            'primary': True,
            'name': 'mozillians-primary-{0}'.format(self.pk)
        }
        # We have an IdpProfile marked as primary (login identity)
        # If there is not an idp profile, the self.email is the one that is used to login
        if primary_idp.exists():
            primary_email['value'] = primary_idp[0].email
            primary_email['name'] = primary_idp[0].get_type_display()

        emails.append(primary_email)

        # Non primary identity profiles
        for idp in self.idp_profiles.filter(primary=False):
            entry = {
                'value': idp.email,
                'verified': True,
                'primary': False,
                'name': '{0}'.format(idp.get_type_display())
            }
            emails.append(entry)

        return emails

    def get_cis_uris(self):
        """Prepares the entry for URIs in the CIS format."""
        accounts = []
        for account in self.externalaccount_set.exclude(type=ExternalAccount.TYPE_EMAIL):
            value = account.get_identifier_url()
            account_type = ExternalAccount.ACCOUNT_TYPES[account.type]
            if value:
                entry = {
                    'value': value,
                    'primary': False,
                    'verified': False,
                    'name': 'mozillians-{}-{}'.format(account_type['name'], account.pk)
                }
                accounts.append(entry)

        return accounts

    def get_cis_groups(self, idp):
        """Prepares the entry for profile groups in the CIS format."""

        # Update strategy: send groups for higher MFA idp
        # Wipe groups from the rest
        idps = list(self.idp_profiles.all().values_list('type', flat=True))

        # if the current idp does not match
        # the greatest number in the list, wipe the groups
        if not idps or idp.type != max(idps) or not idp.is_mfa():
            return []

        memberships = GroupMembership.objects.filter(
            userprofile=self,
            status=GroupMembership.MEMBER,
            group__is_access_group=True
        )
        groups = ['mozilliansorg_{}'.format(m.group.url) for m in memberships]
        return groups

    def get_cis_tags(self):
        """Prepares the entry for profile tags in the CIS format."""
        memberships = GroupMembership.objects.filter(
            userprofile=self,
            status=GroupMembership.MEMBER
        ).exclude(
            group__is_access_group=True
        )

        tags = [m.group.url for m in memberships]
        return tags

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
        autovouch = kwargs.pop('autovouch', True)

        super(UserProfile, self).save(*args, **kwargs)
        # Auto_vouch follows the first save, because you can't
        # create foreign keys without a database id.

        if self.is_complete:
            send_userprofile_to_cis.delay(self.pk)

        if autovouch:
            self.auto_vouch()


class IdpProfile(models.Model):
    """Basic Identity Provider information for Profiles."""
    PROVIDER_PASSWORDLESS = 10
    PROVIDER_GOOGLE = 20
    PROVIDER_GITHUB = 30
    PROVIDER_LDAP = 40

    PROVIDER_TYPES = (
        (PROVIDER_GITHUB, 'Github Provider',),
        (PROVIDER_LDAP, 'LDAP Provider',),
        (PROVIDER_PASSWORDLESS, 'Passwordless Provider',),
        (PROVIDER_GOOGLE, 'Google Provider',),

    )
    profile = models.ForeignKey(UserProfile, related_name='idp_profiles')
    type = models.IntegerField(choices=PROVIDER_TYPES,
                               default=None,
                               null=True,
                               blank=False)
    # Auth0 required data
    auth0_user_id = models.CharField(max_length=1024, default='', blank=True)
    primary = models.BooleanField(default=False)
    email = models.EmailField(blank=True, default='')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    privacy = models.PositiveIntegerField(default=MOZILLIANS, choices=PRIVACY_CHOICES_WITH_PRIVATE)
    primary_contact_identity = models.BooleanField(default=False)

    def get_provider_type(self):
        """Helper method to autopopulate the model type given the user_id."""
        if 'ad|' in self.auth0_user_id:
            return self.PROVIDER_LDAP

        if 'github|' in self.auth0_user_id:
            return self.PROVIDER_GITHUB

        if 'google-oauth2|' in self.auth0_user_id:
            return self.PROVIDER_GOOGLE

        if 'email|' in self.auth0_user_id:
            return self.PROVIDER_PASSWORDLESS

        return None

    def is_mfa(self):
        """Helper method to check if IdpProfile is MFA-ed"""

        return self.type in [self.PROVIDER_GITHUB, self.PROVIDER_LDAP]

    def save(self, *args, **kwargs):
        """Custom save method.

        Provides a default contact identity and a helper to assign the provider type.
        """
        self.type = self.get_provider_type()
        # If there isn't a primary contact identity, create one
        if not (IdpProfile.objects.filter(profile=self.profile,
                                          primary_contact_identity=True).exists()):
            self.primary_contact_identity = True
        super(IdpProfile, self).save(*args, **kwargs)

    def __unicode__(self):
        return u'{}|{}|{}'.format(self.profile, self.type, self.email)

    class Meta:
        unique_together = ('profile', 'type', 'email')


class Vouch(models.Model):
    vouchee = models.ForeignKey(UserProfile, related_name='vouches_received')
    voucher = models.ForeignKey(UserProfile, related_name='vouches_made',
                                null=True, default=None, blank=True,
                                on_delete=models.SET_NULL)
    description = models.TextField(max_length=500, verbose_name=_lazy(u'Reason for Vouching'),
                                   default='')
    autovouch = models.BooleanField(default=False)
    date = models.DateTimeField()

    class Meta:
        verbose_name_plural = 'vouches'
        unique_together = ('vouchee', 'voucher')
        ordering = ['-date']

    def __unicode__(self):
        return u'{0} vouched by {1}'.format(self.vouchee, self.voucher)


class AbuseReport(models.Model):
    TYPE_SPAM = 'spam'
    TYPE_INAPPROPRIATE = 'inappropriate'

    REPORT_TYPES = (
        (TYPE_SPAM, 'Spam profile'),
        (TYPE_INAPPROPRIATE, 'Inappropriate content')
    )

    reporter = models.ForeignKey(UserProfile, related_name='abuses_reported', null=True)
    profile = models.ForeignKey(UserProfile, related_name='abuses')
    type = models.CharField(choices=REPORT_TYPES, max_length=30, blank=False, default='')
    is_akismet = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


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
    TYPE_EMAIL = 'EMAIL'
    TYPE_MDN = 'MDN'
    TYPE_SUMO = 'SUMO'
    TYPE_FACEBOOK = 'FACEBOOK'
    TYPE_TWITTER = 'TWITTER'
    TYPE_AIM = 'AIM'
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
    TYPE_MOLOCATION = 'MOZILLALOCATION'
    TYPE_MOPONTOON = 'MOZILLAPONTOON'
    TYPE_TRANSIFEX = 'TRANSIFEX'
    TYPE_TELEGRAM = 'TELEGRAM'

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
        TYPE_EMAIL: {'name': 'Alternate email address',
                     'url': '',
                     'validator': validate_email},
        TYPE_BITBUCKET: {'name': 'Bitbucket',
                         'url': 'https://bitbucket.org/{identifier}',
                         'validator': validate_username_not_url},
        TYPE_MDN: {'name': 'MDN',
                   'url': 'https://developer.mozilla.org/profiles/{identifier}',
                   'validator': validate_username_not_url},
        TYPE_MOLOCATION: {'name': 'Mozilla Location Service',
                          'url': 'https://location.services.mozilla.com/leaders#{identifier}',
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
                        'url': 'https://www.linkedin.com/in/{identifier}/',
                        'validator': validate_linkedin},
        TYPE_JABBER: {'name': 'XMPP/Jabber',
                      'url': '',
                      'validator': validate_email},
        TYPE_DISCOURSE: {'name': 'Mozilla Discourse',
                         'url': 'https://discourse.mozilla.org/users/{identifier}',
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
        TYPE_MOPONTOON: {'name': 'Mozilla Pontoon',
                         'url': 'https://pontoon.mozilla.org/contributor/{identifier}/',
                         'validator': validate_email},
        TYPE_TRANSIFEX: {'name': 'Transifex',
                         'url': 'https://www.transifex.com/accounts/profile/{identifier}/',
                         'validator': validate_username_not_url},
        TYPE_TELEGRAM: {'name': 'Telegram',
                        'url': 'https://telegram.me/{identifier}',
                        'validator': validate_username_not_url},
    }

    user = models.ForeignKey(UserProfile)
    identifier = models.CharField(max_length=255, verbose_name=_lazy(u'Account Username'))
    type = models.CharField(max_length=30,
                            choices=sorted([(k, v['name']) for (k, v) in ACCOUNT_TYPES.iteritems()
                                            if k != TYPE_EMAIL], key=lambda x: x[1]),
                            verbose_name=_lazy(u'Account Type'))
    privacy = models.PositiveIntegerField(default=MOZILLIANS, choices=PRIVACY_CHOICES_WITH_PRIVATE)

    class Meta:
        ordering = ['type']
        unique_together = ('identifier', 'type', 'user')

    def get_identifier_url(self):
        url = self.ACCOUNT_TYPES[self.type]['url'].format(identifier=urlquote(self.identifier))
        if self.type == 'LINKEDIN' and '://' in self.identifier:
            return self.identifier

        return iri_to_uri(url)

    def unique_error_message(self, model_class, unique_check):
        if model_class == type(self) and unique_check == ('identifier', 'type', 'user'):
            return _('You already have an account with this name and type.')
        else:
            return super(ExternalAccount, self).unique_error_message(model_class, unique_check)

    def __unicode__(self):
        return self.type


class Language(models.Model):
    code = models.CharField(max_length=63, choices=get_languages_for_locale('en'))
    userprofile = models.ForeignKey(UserProfile)

    class Meta:
        ordering = ['code']
        unique_together = ('code', 'userprofile')

    def __unicode__(self):
        return self.code

    def get_english(self):
        return self.get_code_display()

    def get_native(self):
        if not getattr(self, '_native', None):
            languages = get_languages_for_locale(self.code)
            for code, language in languages:
                if code == self.code:
                    self._native = language
                    break
        return self._native

    def unique_error_message(self, model_class, unique_check):
        if (model_class == type(self) and unique_check == ('code', 'userprofile')):
            return _('This language has already been selected.')
        return super(Language, self).unique_error_message(model_class, unique_check)
