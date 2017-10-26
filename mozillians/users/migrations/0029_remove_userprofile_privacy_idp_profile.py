# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0028_auto_20171024_0457'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='userprofile',
            name='privacy_idp_profile',
        ),
    ]
