from django.contrib.auth.utils import get_random_string
from django.core.mail import send_mail
from django.db import models
from django.dispatch import receiver

from funfactory.urlresolvers import reverse
from funfactory.utils import absolutify
from tower import ugettext as _


class Invite(models.Model):
    #: The ``uid`` of the vouched Mozillian who is doing the inviting.
    inviter = models.CharField(max_length=32, editable=False)

    #: This is the email address of where the invitation is sent.
    recipient = models.EmailField()

    #: The ``uid`` of the newly created user who has redeemed the invite.
    redeemer = models.CharField(max_length=32, editable=False)

    #: Randomly generated invite code.  This code is used in the
    #: :ref:`registration` system.
    code = models.CharField(max_length=32, editable=False, unique=True)

    #: The date the invite was redeemed.
    redeemed = models.DateTimeField(null=True, editable=False)

    #: The date the invite was created.
    created = models.DateTimeField(auto_now_add=True, editable=False)

    def get_url(self, absolute=True):
        """A url that can be used to redeem this invite."""
        return absolutify(reverse('register')) + '?code=' + self.code

    def send(self, sender=None):
        subject = _('Become a Mozillian')
        message = _("Hi, I'm sending you this because I think you should "
                    'join mozillians.org, the community directory for '
                    'Mozilla contributors like you. You can create a '
                    'profile for yourself about what you do in the '
                    'community as well as search for other contributors '
                    'to learn more about them or get in touch.  Check it '
                    'out.')
        # l10n: %s is the registration link.
        link = _("Join Mozillians: %s") % self.get_url()
        message = "%s\n\n%s" % (message, link)
        send_mail(subject, message, sender or 'no-reply@mozillians.org',
                  [self.recipient])

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
