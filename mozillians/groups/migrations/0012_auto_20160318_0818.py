# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0011_auto_20160317_0955'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='accepting_new_members',
            field=models.CharField(default=b'yes', max_length=10, verbose_name='Accepting new members', choices=[(b'yes', 'Open'), (b'by_request', 'Reviewed'), (b'no', 'Closed')]),
        ),
        migrations.AlterField(
            model_name='invite',
            name='redeemer',
            field=models.ForeignKey(related_name='groups_invited', verbose_name='Redeemer', to='users.UserProfile'),
        ),
    ]
