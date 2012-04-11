import uuid
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import models
from django.db.models import signals as dbsignals
from django.dispatch import receiver

from elasticutils import S
from elasticutils.models import SearchMixin
from sorl.thumbnail import ImageField
from PIL import Image, ImageOps
from tower import ugettext as _, ugettext_lazy as _lazy

from groups.models import Group, Skill
from phonebook.helpers import gravatar

# This is because we are using MEDIA_ROOT wrong in 1.4
from django.core.files.storage import FileSystemStorage
fs = FileSystemStorage(location=settings.UPLOAD_ROOT,
                       base_url='/media/uploads/')


class UserProfile(SearchMixin, models.Model):
    # This field is required.
    user = models.OneToOneField(User)

    # Other fields here
    is_vouched = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True, default=datetime.now)
    website = models.URLField(max_length=200, verbose_name=_lazy(u'Website'),
                              default='', blank=True, null=True)

    # Foreign Keys and Relationships
    vouched_by = models.ForeignKey('UserProfile', null=True, default=None,
                                   on_delete=models.SET_NULL)

    groups = models.ManyToManyField('groups.Group')
    skills = models.ManyToManyField('groups.Skill')
    bio = models.TextField(verbose_name=_lazy(u'Bio'), default='', blank=True)
    photo = ImageField(default='', blank=True, storage=fs,
                       upload_to='userprofile')
    display_name = models.CharField(max_length=255, default='', blank=True)
    ircname = models.CharField(max_length=63,
                               verbose_name=_lazy(u'IRC Nickname'),
                               default='', blank=True)

    @property
    def full_name(self):
        return '%s %s' % (self.user.first_name, self.user.last_name)

    class Meta:
        db_table = 'profile'

    def __unicode__(self):
        """Return this user's name when their profile is called."""
        return self.display_name

    def anonymize(self):
        """Remove personal info from a user"""

        for name in ['first_name', 'last_name', 'email']:
            setattr(self.user, name, '')

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
        """ Alters membership to Groups and Skillz """
        if model is Group:
            m2mfield = self.groups
        elif model is Skill:
            m2mfield = self.skills

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
        """
        Tests if a user has all the information needed to move on past the
        original registration view
        """
        return self.display_name and self.display_name != ' '

    def photo_url(self):
        if self.photo:
            return self.photo.url

        return gravatar(self.user.email)

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

    def _email_now_vouched(self):
        """Email this user, letting them know they are now vouched."""
        subject = _(u'You are now vouched on Mozillians!')
        message = _(u"You've now been vouched on Mozillians.org. "
                     "You'll now be able to search, vouch "
                     "and invite other Mozillians onto the site.")
        send_mail(subject, message, 'no-reply@mozillians.org',
                  [self.user.email])

    def fields(self):
        """Method used by elasticutils."""
        attrs = (
            'id', 'is_vouched', 'website', 'bio', 'display_name', 'ircname')
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
                  'last_name__startswith', 'ircname')
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


@receiver(dbsignals.post_save, sender=UserProfile)
def resize_photo(sender, instance, **kwargs):
    if instance.photo:
        path = str(instance.photo.path)
        img = Image.open(path)
        img = ImageOps.fit(img, (300, 300), Image.ANTIALIAS, 0, (0.5, 0.5))
        img.save(path)


@receiver(dbsignals.post_save, sender=User)
@receiver(dbsignals.post_save, sender=UserProfile)
def update_search_index(sender, instance, **kw):
    from elasticutils import tasks
    tasks.index_objects.delay(UserProfile, [instance.id])


@receiver(dbsignals.post_delete, sender=UserProfile)
def remove_from_search_index(sender, instance, **kw):
    from elasticutils import tasks
    tasks.unindex_objects.delay(sender, [instance.id])
