# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0018_auto_20170502_0346'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='auth0_user_id',
            field=models.CharField(default=b'', max_length=1024, blank=True),
        ),
    ]
