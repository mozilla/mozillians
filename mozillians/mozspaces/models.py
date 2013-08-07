import os
import uuid

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from product_details import product_details
from pytz import common_timezones
from sorl.thumbnail import ImageField


COUNTRIES = product_details.get_regions('en-US').items()
COUNTRIES = sorted(COUNTRIES, key=lambda country: country[1])


def _calculate_photo_filename(instance, filename):
    """Generate a unique filename for uploaded photo."""
    return os.path.join(settings.MOZSPACE_PHOTO_DIR,
                        str(uuid.uuid4()) + '.jpg')


class MozSpace(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=300)
    region = models.CharField(max_length=100, blank=True, default='')
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=5, choices=COUNTRIES)
    timezone = models.CharField(
        max_length=100, choices=zip(common_timezones, common_timezones))
    lon = models.FloatField()
    lat = models.FloatField()
    phone = models.CharField(max_length=100, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    coordinator = models.ForeignKey(User)
    extra_text = models.TextField(blank=True, default='')
    cover_photo = models.ForeignKey('Photo', null=True, blank=True,
                                    related_name='featured_mozspace')

    def __unicode__(self):
        return self.name


class Keyword(models.Model):
    keyword = models.CharField(max_length=50, unique=True)
    mozspace = models.ForeignKey(MozSpace, related_name='keywords')

    def save(self, *args, **kwargs):
        self.keyword = self.keyword.lower()
        super(Keyword, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.keyword


class Photo(models.Model):
    photofile = ImageField(upload_to=_calculate_photo_filename)
    mozspace = models.ForeignKey(MozSpace, related_name='photos')

    def __unicode__(self):
        return unicode(self.id)
