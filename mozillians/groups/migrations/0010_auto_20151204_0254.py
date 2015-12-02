# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0009_auto_20151130_1020'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='invalidation_days',
            field=models.PositiveIntegerField(default=None, null=True, verbose_name=b'Invalidation days', blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='groupmembership',
            name='updated_on',
            field=models.DateTimeField(auto_now=True, null=True),
            preserve_default=True,
        ),
    ]
