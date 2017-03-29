# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0015_auto_20170323_1202'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='allows_community_sites',
        ),
        migrations.RemoveField(
            model_name='userprofile',
            name='allows_mozilla_sites',
        ),
    ]
