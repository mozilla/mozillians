# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0005_remove_groupmembership_invalidate'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='terms',
            field=models.TextField(default=b'', verbose_name=b'Terms', blank=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='groupmembership',
            name='status',
            field=models.CharField(max_length=15, choices=[('member', 'Member'), ('pending_terms', 'Pending terms'), ('pending', 'Pending')]),
            preserve_default=True,
        ),
    ]
