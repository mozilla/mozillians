from datetime import datetime

from django.contrib.auth.models import User
from django.db import models

from tower import ugettext_lazy as _


class Task(models.Model):
    contact = models.ForeignKey(User, verbose_name=_(u'Contact Person'),
                                related_name="tasks")
    summary = models.CharField(_(u'Summary'), max_length=255)
    instructions = models.TextField(_(u'Instructions'), blank=True)
    groups = models.ManyToManyField('groups.Group', blank=True,
                                    verbose_name=_(u'Groups'))
    deadline = models.DateField(_(u'Deadline'), blank=True, null=True,
                                help_text=_(u'yyyy-mm-dd'))
    created = models.DateTimeField(_(u'Created Date'), default=datetime.utcnow,
                                   editable=False)
    disabled = models.BooleanField(_(u'Disabled'), default=False)

    def __unicode__(self):
        return u'{0} ({1})'.format(self.summary, self.contact)
