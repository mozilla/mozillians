# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_auto_20151124_0647'),
        ('groups', '0006_auto_20151130_0902'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='curators',
            field=models.ManyToManyField(related_name='groups_curated_new', to='users.UserProfile'),
            preserve_default=True,
        ),
    ]
