# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0002_auto_20150820_0822'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupmembership',
            name='invalidate',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
