import random
import string

from django.db import models
from django.dispatch import receiver

from commons.helpers import absolutify
from commons.urlresolvers import reverse
from manage import path


class Invite(models.Model):
    # uid of the person inviting, ozten can clarify size
    inviter = models.CharField(max_length=32, editable=False)
    destination = models.EmailField()
    code = models.CharField(max_length=32, editable=False, unique=True)
    redeemed = models.DateTimeField(null=True, editable=False)
    created = models.DateTimeField(auto_now_add=True, editable=False)

    def get_url(self, absolute=True):
        return absolutify(reverse('register')) + '?code=' + self.code

    class Meta:
        db_table = 'invite'


def _get_random_name(num):
    f = open(path('RANDOMWORDS.txt'))
    lines = f.readlines()
    sample = random.sample(lines, num)
    return [s.strip().replace(' ', '') for s in sample]


def _random_alphanum(num):
    sample = random.sample(string.printable[:63], num)
    return ''.join(sample)


def _generate_code():
    while True:
        name = _get_random_name(2)
        alpha = _random_alphanum(2)
        code = '%s%s%s' % (name[0], alpha, name[1])
        yield code[:32]


@receiver(models.signals.pre_save, sender=Invite)
def generate_code(sender, instance, raw, using, **kwargs):
    if instance.code:
        return

    g = _generate_code()

    # 10 tries for uniqueness
    for i in xrange(10):
        code = g.next()
        if Invite.objects.filter(code=code).count():
            continue

    instance.code = code
