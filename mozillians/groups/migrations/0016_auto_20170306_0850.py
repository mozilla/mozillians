# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0015_groupmembership_needs_renewal'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invite',
            name='group',
            field=models.ForeignKey(related_name='invited', to='groups.Group'),
        ),
    ]
