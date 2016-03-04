# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_auto_20160302_0856'),
        ('groups', '0010_auto_20151204_0254'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('accepted', models.NullBooleanField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('group', models.ForeignKey(related_name='invites', to='groups.Group')),
                ('inviter', models.ForeignKey(related_name='group_invites', on_delete=django.db.models.deletion.SET_NULL, verbose_name='Inviter', to='users.UserProfile', null=True)),
                ('redeemer', models.ForeignKey(related_name='group_invites_redeemed', verbose_name='Redeemer', to='users.UserProfile')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='invite',
            unique_together=set([('group', 'redeemer')]),
        ),
    ]
