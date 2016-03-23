# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0012_auto_20160318_0818'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invite',
            name='accepted',
            field=models.BooleanField(default=False),
        ),
    ]
