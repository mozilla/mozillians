# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_auto_20150820_0822'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='apiapp',
            name='owner',
        ),
        migrations.DeleteModel(
            name='APIApp',
        ),
    ]
