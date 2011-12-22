import urllib

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.core.mail import send_mail
from django.db import models
from django.dispatch import receiver

from funfactory.utils import absolutify
from funfactory.urlresolvers import reverse
from tower import ugettext as _

import larper
from groups.models import Group
from phonebook.models import get_random_string


class UserProfileManager(models.Manager):
    """Custom manager that can query via LDAP attributes."""

    def get_by_unique_id(self, uid):
        """Given an LDAP uniqueIdentifier, find a match."""
        rs = larper.get_user_by_uid(uid)
        mail = rs[1]['mail'][0]
        return User.objects.get(email=mail).get_profile()


class UserProfile(models.Model):
    # This field is required.
    user = models.OneToOneField(User)

    # Other fields here
    confirmation_code = models.CharField(max_length=32, editable=False,
                                         unique=True)
    is_confirmed = models.BooleanField(default=False)
    is_vouched = models.BooleanField(default=False)
    website = models.URLField(max_length=200, null=True)

    # Foreign Keys and Relationships
    vouched_by = models.ForeignKey('UserProfile', null=True)
    groups = models.ManyToManyField('groups.Group')

    objects = UserProfileManager()

    class Meta:
        db_table = 'profile'

    def vouch(self, vouchee, system=True, commit=True):
        changed = system # have we changed anything?
        if system:
            self.is_vouched = True
            self.get_ldap_person()
            my_uid = self.get_ldap_person()[1]['uniqueIdentifier'][0]
            their_uid = 'ZUUL'
            larper.record_vouch(their_uid, my_uid)

        if vouchee and vouchee.is_vouched:
            changed = True
            self.is_vouched = True
            self.vouched_by = vouchee
            # TODO: remove this when we take vouch status out of LDAP.
            #       - need to do search filtering of vouch from mysql
            #       - checking of vouch status via profile instead of LDAP
            self.get_ldap_person()
            my_uid = self.get_ldap_person()[1]['uniqueIdentifier'][0]
            their_uid = vouchee.get_ldap_person()[1]['uniqueIdentifier'][0]
            larper.record_vouch(my_uid, their_uid)

        if commit and changed:
            self.save()

            # Email the user and tell them they were vouched.
            self._email_now_vouched()

    def get_confirmation_url(self):
        url = (absolutify(reverse('confirm')) + '?code=' +
               self.confirmation_code)
        return url

    def get_send_confirmation_url(self):
        url = (reverse('send_confirmation') + '?' +
               urllib.urlencode({'user': self.user.username}))
        return url

    def get_unique_id(self):
        r = self.get_ldap_person()
        return r[1]['uniqueIdentifier'][0]

    def get_ldap_person(self):
        email = self.user.email or self.user.username
        return larper.get_user_by_email(email)

    def _email_now_vouched(self):
        """Email this user, letting them know they are now vouched."""
        subject = _(u'You are now vouched on Mozillians!')
        message = _(u"You've now been vouched on Mozillians.org. "
                     "You'll now be able to search, vouch "
                     "and invite other Mozillians onto the site.")
        send_mail(subject, message, 'no-reply@mozillians.org',
                  [self.user.username])

    def __unicode__(self):
        """Return this user's name when their profile is called."""
        return self.user.first_name


class Anonymous(AnonymousUser):
    """Anonymous user provides minimum data for views and templates."""
    def __init__(self):
        super(Anonymous, self).__init__()
        self.unique_id = '0'


@receiver(models.signals.post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(models.signals.pre_save, sender=UserProfile)
def generate_code(sender, instance, raw, using, **kwargs):
    if instance.confirmation_code:
        return

    # 10 tries for uniqueness
    for i in xrange(10):
        code = get_random_string(32)
        if UserProfile.objects.filter(confirmation_code=code).count():
            continue

    instance.confirmation_code = code


@receiver(models.signals.pre_save, sender=UserProfile)
def auto_vouch(sender, instance, raw, using, **kwargs):
    """Auto vouch mozilla.com users."""
    username = instance.user.username
    if any(username.endswith('@' + x) for x in settings.AUTO_VOUCH_DOMAINS):
        instance.vouch(None, system=True, commit=False)


@receiver(models.signals.post_save, sender=UserProfile)
def add_to_staff_group(sender, instance, created, **kwargs):
    """Add all mozilla.com users to the "staff" group upon creation."""
    if created:
        username = instance.user.username
        if (any(username.endswith('@' + x) for x in
                                               settings.AUTO_VOUCH_DOMAINS)):
            instance.groups.add(Group.objects.get(name='staff', system=True))
