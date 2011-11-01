import urllib

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.dispatch import receiver

from funfactory.utils import absolutify
from funfactory.urlresolvers import reverse

import larper
from groups.models import Group
from phonebook.models import get_random_string


class UserProfile(models.Model):
    # This field is required.
    user = models.OneToOneField(User)

    # Other fields here
    confirmation_code = models.CharField(max_length=32, editable=False,
                                         unique=True)
    is_confirmed = models.BooleanField(default=False)
    is_vouched = models.BooleanField(default=False)
    vouched_by = models.ForeignKey('UserProfile', null=True)
    groups = models.ManyToManyField('groups.Group')

    class Meta:
        db_table = 'profile'

    def vouch(self, vouchee):
        if vouchee and vouchee.is_vouched:
            self.is_vouched = True
            self.vouched_by = vouchee
            self.save()
            # TODO: remove this when we take vouch status out of LDAP.
            #       - need to do search filtering of vouch from mysql
            #       - checking of vouch status via profile instead of LDAP
            self.get_ldap_person()
            my_uid = self.get_ldap_person()[1]['uniqueIdentifier'][0]
            their_uid = vouchee.get_ldap_person()[1]['uniqueIdentifier'][0]
            larper.record_vouch(my_uid, their_uid)

    def get_confirmation_url(self):
        url = (absolutify(reverse('confirm')) + '?code=' +
               self.confirmation_code)
        return url

    def get_send_confirmation_url(self):
        url = (reverse('send_confirmation') + '?' +
               urllib.urlencode({'user': self.user.username}))
        return url

    def get_ldap_person(self):
        return larper.get_user_by_email(self.user.email)

    def __unicode__(self):
        """Return this user's name when their profile is called."""
        return self.user.first_name


@receiver(models.signals.post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        profile = UserProfile.objects.create(user=instance)

        if any(instance.email.endswith('@' + d)
               for d in settings.AUTO_VOUCH_DOMAINS):
            profile.groups.add(Group.objects.get(name='staff', system=True))

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
