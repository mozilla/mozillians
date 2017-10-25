# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import mozillians.users.models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_auto_20170329_0339'),
    ]

    operations = [
        migrations.AlterField(
            model_name='apiv2app',
            name='privacy_level',
            field=mozillians.users.models.PrivacyField(default=4, choices=[(1, 'Private'), (3, 'Mozillians'), (4, 'Public')]),
        ),
    ]
