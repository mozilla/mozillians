# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0003_groupmembership_invalidate'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='description',
            field=models.TextField(default=b'', max_length=1024, verbose_name='Description', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='group',
            name='new_member_criteria',
            field=models.TextField(default=b'', help_text='Specify the criteria you will use to decide whether or not you will accept a membership request.', max_length=1024, verbose_name='New Member Criteria', blank=True),
            preserve_default=True,
        ),
    ]
