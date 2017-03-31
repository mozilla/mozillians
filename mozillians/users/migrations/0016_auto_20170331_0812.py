# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def migrate_countries(apps, schema_editor):
    Country = apps.get_model('cities_light', 'Country')
    UserProfile = apps.get_model('users', 'UserProfile')

    try:
        qs = UserProfile.objects.filter(geo_country__name='Netherlands')
        country = Country.objects.get(name='Netherlands')
        kwargs = {
            'country': country,
        }
        qs.update(**kwargs)
    except:
        pass


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_auto_20170323_1202'),
    ]

    operations = [
        migrations.RunPython(migrate_countries, backwards),
    ]
