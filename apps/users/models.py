import os
import time
import urllib

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models
from django.db.models import signals as dbsignals
from django.dispatch import receiver

from elasticutils import S
from elasticutils.models import SearchMixin
from funfactory.utils import absolutify
from funfactory.urlresolvers import reverse
from statsd import statsd
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


class UserProfile(SearchMixin, models.Model):
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
    bio = models.CharField(max_length=255, default='')
    photo = models.BooleanField(default=False)
    display_name = models.CharField(max_length=30)
    ircname = models.CharField(max_length=63, blank=True)
    objects = UserProfileManager()

    class Meta:
        db_table = 'profile'

    def vouch(self, vouched_by, system=True, commit=True):
        changed = system  # do we need to do a vouch?
        if system:
            self.is_vouched = True

        if vouched_by and vouched_by.is_vouched:
            changed = True
            self.is_vouched = True
            self.vouched_by = vouched_by

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

    def get_photo_url(self, cachebust=False):
        """Gets a user's userpic URL.  Appends cachebusting if requested."""

        if self.photo:
            url = '%s/%d.jpg' % (settings.USERPICS_URL, self.user_id)

            if cachebust:
                url += '?%d' % int(time.time())
        else:
            url = settings.MEDIA_URL + 'img/unknown.png'

        return url

    def get_photo_file(self):
        return '%s/%d.jpg' % (settings.USERPICS_PATH, self.user_id)

    # TODO: get rid of this when larper is gone ETA Apr-2012
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

    @property
    def full_name(self):
        "%s %s" % (self.user.first_name, self.user.last_name)

    def __unicode__(self):
        """Return this user's name when their profile is called."""
        return self.user.first_name

    def fields(self):
        attrs = ('id', 'is_confirmed', 'is_vouched', 'website',
                 'bio', 'photo', 'display_name', 'ircname')
        d = dict((a, getattr(self, a)) for a in attrs)
        # user data
        attrs = ('username', 'first_name', 'last_name', 'email', 'last_login',
                 'date_joined')
        d.update(dict((a, getattr(self.user, a)) for a in attrs))
        # Index group ids... for fun.
        groups = list(self.groups.values_list('name', flat=True))
        d.update(dict(groups=groups))
        return d

    @classmethod
    def search(cls, query, vouched=None):
        """Sensible default search for UserProfiles."""
        query = query.lower().strip()
        fields = ('first_name__text', 'last_name__text', 'display_name__text',
                  'username__text', 'bio__text', 'website__text',
                  'email__text', 'groups__text', 'first_name__startswith',
                  'last_name__startswith')
        q = dict((field, query) for field in fields)
        s = S(cls).query(or_=q)
        if vouched is not None:
            s = s.filter(is_vouched=vouched)
        return s


@receiver(models.signals.post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    dn = '%s %s' % (instance.first_name, instance.last_name)

    if created:
        UserProfile.objects.create(user=instance, display_name=dn)
    else:
        u = UserProfile.objects.get(user=instance)
        u.display_name = dn
        u.save()


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
    if not instance.id:
        email = instance.user.email
        if any(email.endswith('@' + x) for x in settings.AUTO_VOUCH_DOMAINS):
            instance.vouch(None, system=True, commit=False)


@receiver(models.signals.post_save, sender=UserProfile)
def add_to_staff_group(sender, instance, created, **kwargs):
    """Add all mozilla.com users to the "staff" group upon creation."""
    if created:
        email = instance.user.email
        if (any(email.endswith('@' + x) for x in
                                               settings.AUTO_VOUCH_DOMAINS)):
            instance.groups.add(Group.objects.get(name='staff', system=True))


@receiver(dbsignals.post_save, sender=User)
@receiver(dbsignals.post_save, sender=UserProfile)
def update_search_index(sender, instance, **kw):
    from elasticutils import tasks
    tasks.index_objects.delay(UserProfile, [instance.id])


@receiver(dbsignals.post_delete, sender=UserProfile)
def remove_from_search_index(sender, instance, **kw):
    from elasticutils import tasks
    tasks.unindex_objects.delay(sender, [instance.id])


@receiver(dbsignals.post_delete, sender=UserProfile)
def remove_photos(sender, instance, **kw):
    """Deletes photo files."""
    # TODO: if this gets slow, give it to celery.
    with statsd.timer('photos.remove'):
        if instance.photo:
            os.remove(instance.get_photo_file())
