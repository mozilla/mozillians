# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Invite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('recipient', models.EmailField(max_length=75, verbose_name='Recipient')),
                ('code', models.CharField(unique=True, max_length=32)),
                ('reason', models.TextField(default=b'', max_length=500)),
                ('redeemed', models.DateTimeField(null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('inviter', models.ForeignKey(related_name='invites', verbose_name='Inviter', to='users.UserProfile', null=True)),
                ('redeemer', models.OneToOneField(null=True, blank=True, to='users.UserProfile', verbose_name='Redeemer')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
