# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import mozillians.users.models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0006_auto_20160505_0348'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='full_name_local',
            field=models.CharField(default=b'', max_length=255, verbose_name='Name in local language', blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='privacy_full_name_local',
            field=mozillians.users.models.PrivacyField(default=3, choices=[(3, 'Mozillians'), (4, 'Public')]),
        ),
    ]
