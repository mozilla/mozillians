from datetime import datetime
from django.contrib.auth.models import User
from django.db import models


class Task(models.Model):
    contact = models.ForeignKey(User, related_name="tasks")
    summary = models.CharField(max_length=255)
    instructions = models.TextField(blank=True)
    groups = models.ManyToManyField('groups.Group', blank=True)
    deadline = models.DateField(blank=True)
    created = models.DateTimeField(default=datetime.utcnow, editable=False)
    disabled = models.BooleanField(default=False)

    def __unicode__(self):
        return u"{0} ({1})".format(self.summary, self.contact)
