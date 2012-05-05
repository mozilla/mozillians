from django.contrib.auth.utils import get_random_string
from django.core.mail import send_mail
from django.db import models
from django.dispatch import receiver
from django.template.loader import get_template

from funfactory.urlresolvers import reverse
from funfactory.utils import absolutify
from tower import ugettext as _


class Invite(models.Model):
    #: The person doing the inviting.
    inviter = models.ForeignKey('users.UserProfile', related_name='invites',
                                null=True)

    #: This is the email address of where the invitation is sent.
    recipient = models.EmailField()

    # This is the message sent alongside the invite. "Hey you're cool."
    message = models.TextField(blank=True)

    #: The person who redeemed this invite.
    redeemer = models.OneToOneField('users.UserProfile', null=True)

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
        """Mail this invite to the specified user.

        Includes the name and email of the inviting person, if available.
        """
        if sender:
            sender = '%s %s (%s)' % (sender.user.first_name,
                                     sender.user.last_name,
                                     sender.user.email)

        subject = _('Become a Mozillian')

        template = get_template('phonebook/invite_email.txt')

        message = template.render({
            'personal_message': self.message,
            'sender': sender or _('A fellow Mozillian'),
            'link': self.get_url()})

        # Manually replace quotes and double-quotes as these get
        # escaped by the template and this makes the message look bad.
        filtered_message = message.replace('&#34;', '"').replace('&#39;', "'")

        send_mail(subject, filtered_message, 'no-reply@mozillians.org',
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
