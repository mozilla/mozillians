import urllib

from django.contrib.auth.models import User
from django.db import models
from django.dispatch import receiver

from funfactory.utils import absolutify
from funfactory.urlresolvers import reverse

from phonebook.models import get_random_string


class UserProfile(models.Model):
    # This field is required.
    user = models.OneToOneField(User)

    # Other fields here
    confirmation_code = models.CharField(max_length=32, editable=False,
                                         unique=True)
    is_confirmed = models.BooleanField(default=False)

    class Meta:
        db_table = 'profile'

    def get_confirmation_url(self):
        url = (absolutify(reverse('confirm')) + '?code=' +
               self.confirmation_code)
        return url

    def get_send_confirmation_url(self):
        url = (reverse('send_confirmation') + '?' +
               urllib.urlencode({'user': self.user.username}))
        return url


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
