import os
import uuid

from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.timezone import now

import bleach
from jinja2 import Markup
from sorl.thumbnail import ImageField

from mozillians.announcements.managers import AnnouncementManager


ALLOWED_TAGS = ['em', 'strong', 'a', 'u']


def _calculate_image_filename(instance, filename):
    """Generate a unique filename for uploaded image."""
    return os.path.join(settings.ANNOUNCEMENTS_PHOTO_DIR,
                        str(uuid.uuid4()) + '.jpg')


class Announcement(models.Model):
    objects = AnnouncementManager()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=255)
    text = models.TextField(max_length=750)
    image = ImageField(default='', blank=True,
                       help_text=('60x60 pixel image recommended. Image '
                                  'will be rescaled automatically to '
                                  'a square.'),
                       upload_to=_calculate_image_filename)
    publish_from = models.DateTimeField(help_text='Timezone is %s' % settings.TIME_ZONE)
    publish_until = models.DateTimeField(blank=True, null=True,
                                         help_text='Timezone is %s' % settings.TIME_ZONE)

    def clean(self):
        self.text = bleach.clean(self.text, tags=ALLOWED_TAGS, strip=True)
        if self.publish_until and self.publish_until < self.publish_from:
            raise ValidationError('Publish until must come after publish from.')

    @property
    def published(self):
        _now = now()
        return ((self.publish_from <= _now) and
                (self.publish_until > _now if self.publish_until else True))

    def get_template_text(self):
        """Mark text as template safe so html tags are not escaped."""
        return Markup(self.text)

    def __unicode__(self):
        return self.title

    class Meta:
        ordering = ['-publish_from']
        get_latest_by = 'publish_from'
