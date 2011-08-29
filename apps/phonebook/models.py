import random
import string

from django.contrib.auth.utils import get_random_string
from django.db import models
from django.dispatch import receiver

from funfactory.urlresolvers import reverse
from funfactory.utils import absolutify


class Invite(models.Model):
    # uid of the person inviting, ozten can clarify size
    inviter = models.CharField(max_length=32, editable=False)
    recipient = models.EmailField()
    redeemer = models.CharField(max_length=32, editable=False)
    code = models.CharField(max_length=32, editable=False, unique=True)
    redeemed = models.DateTimeField(null=True, editable=False)
    created = models.DateTimeField(auto_now_add=True, editable=False)

    def get_url(self, absolute=True):
        return absolutify(reverse('register')) + '?code=' + self.code

    class Meta:
        db_table = 'invite'


@receiver(models.signals.pre_save, sender=Invite)
def generate_code(sender, instance, raw, using, **kwargs):
    if instance.code:
        return

    # 10 tries for uniqueness
    for i in xrange(10):
        code = get_random_string(5)
        if Invite.objects.filter(code=code).count():
            continue

    instance.code = code
