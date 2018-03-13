# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0018_group_is_access_group'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='is_access_group',
            field=models.BooleanField(default=False, verbose_name=b'Is this an access group?', choices=[(True, 'Access Group'), (False, 'Tag')]),
        ),
    ]
