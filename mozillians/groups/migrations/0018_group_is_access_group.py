# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0017_auto_20170322_0710'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='is_access_group',
            field=models.BooleanField(default=False),
        ),
    ]
