# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_auto_20151124_0647'),
        ('groups', '0010_auto_20151204_0254'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('redeemed', models.DateTimeField(null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('accepted', models.NullBooleanField()),
                ('group', models.ForeignKey(related_name='invites', to='groups.Group')),
                ('inviter', models.ForeignKey(related_name='groups_invites', verbose_name='Inviter', to='users.UserProfile', null=True)),
                ('redeemer', models.OneToOneField(related_name='groups_invites_received', null=True, blank=True, to='users.UserProfile', verbose_name='Redeemer')),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
    ]
