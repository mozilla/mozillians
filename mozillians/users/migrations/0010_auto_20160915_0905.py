# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def migrate_is_spam_flag(apps, schema_editor):
    UserProfile = apps.get_model('users', 'UserProfile')
    AbuseReport = apps.get_model('users', 'AbuseReport')

    for profile in UserProfile.objects.filter(is_spam=True):
        kwargs = {
            'type': 'spam',
            'reporter': None,
            'profile': profile,
            'is_akismet': True
        }
        AbuseReport.objects.create(**kwargs)


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_abusereport'),
    ]

    operations = [
        migrations.RunPython(migrate_is_spam_flag, backwards)
    ]
