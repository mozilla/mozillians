# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mozspaces', '0002_auto_20160302_0856'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mozspace',
            name='email',
            field=models.EmailField(default=b'', max_length=254, blank=True),
        ),
    ]
