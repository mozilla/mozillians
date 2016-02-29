# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('phonebook', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invite',
            name='inviter',
            field=models.ForeignKey(related_name='phonebook_invites', verbose_name='Inviter', to='users.UserProfile', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='invite',
            name='redeemer',
            field=models.OneToOneField(related_name='phonebook_invites_received', null=True, blank=True, to='users.UserProfile', verbose_name='Redeemer'),
            preserve_default=True,
        ),
    ]
