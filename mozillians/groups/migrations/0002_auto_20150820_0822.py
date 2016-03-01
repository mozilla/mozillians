# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('groups', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupmembership',
            name='userprofile',
            field=models.ForeignKey(to='users.UserProfile'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='groupmembership',
            unique_together=set([('userprofile', 'group')]),
        ),
        migrations.AddField(
            model_name='groupalias',
            name='alias',
            field=models.ForeignKey(related_name='aliases', to='groups.Group'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='group',
            name='curator',
            field=models.ForeignKey(related_name='groups_curated', on_delete=django.db.models.deletion.SET_NULL, blank=True, to='users.UserProfile', null=True),
            preserve_default=True,
        ),
    ]
