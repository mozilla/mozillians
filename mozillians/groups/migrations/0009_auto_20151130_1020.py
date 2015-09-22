# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0008_auto_20151130_1013'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='group',
            name='curator',
        ),
        migrations.AlterField(
            model_name='group',
            name='curators',
            field=models.ManyToManyField(related_name='groups_curated', to='users.UserProfile'),
            preserve_default=True,
        ),
    ]
