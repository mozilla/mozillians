from datetime import datetime

from django.db import models
from django.db.models import signals as dbsignals
from django.dispatch import receiver

from elasticutils import S
from elasticutils.models import SearchMixin
from tower import ugettext_lazy as _

from users.models import UserProfile


class Task(SearchMixin, models.Model):
    contact = models.ForeignKey(UserProfile, verbose_name=_(u'Contact'),
                                related_name="created_tasks")
    summary = models.CharField(_(u'Summary'), max_length=255)
    instructions = models.TextField(_(u'Instructions'), blank=True)
    groups = models.ManyToManyField('groups.Group', blank=True,
                                    verbose_name=_(u'Groups'))
    deadline = models.DateField(_(u'Deadline'), blank=True, null=True,
                                help_text=_(u'yyyy-mm-dd'))
    created = models.DateTimeField(_(u'Created Date'), default=datetime.utcnow,
                                   editable=False)
    assigned = models.DateField(_(u'Deadline'), blank=True, null=True,
                                help_text=_(u'yyyy-mm-dd'))
    accepted_by = models.ForeignKey(UserProfile, blank=True, null=True,
                                    verbose_name=_(u'Accepted by'),
                                    related_name='accepted_tasks')
    disabled = models.BooleanField(_(u'Disabled'), default=False)

    def __unicode__(self):
        return u'{0} ({1})'.format(self.summary, self.contact)

    def fields(self):
        attrs = ('id', 'summary', 'instructions', 'deadline',
                 'created', 'disabled')
        return dict((a, getattr(self, a)) for a in attrs)

    @classmethod
    def search(cls, query):
        query = query.lower().strip()
        fields = ('summary__text', 'summary__startswith',
                  'instructions__text')
        q = dict((field, query) for field in fields)
        s = S(cls).query(or_=q).filter(disabled=False)
        return s


@receiver(dbsignals.post_save, sender=Task)
def update_search_index(sender, instance, **kw):
    from elasticutils import tasks as es_tasks
    es_tasks.index_objects.delay(Task, [instance.id])


# This may not be used. Thats ok; it allows us to use Task.delete()
@receiver(dbsignals.post_delete, sender=Task)
def remove_from_search_index(sender, instance, **kw):
    from elasticutils import tasks as es_tasks
    es_tasks.unindex_objects.delay(sender, [instance.id])
