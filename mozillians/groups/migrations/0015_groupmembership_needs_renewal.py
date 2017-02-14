# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0014_group_invite_email_text'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupmembership',
            name='needs_renewal',
            field=models.BooleanField(default=False),
        ),
    ]
