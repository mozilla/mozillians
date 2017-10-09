# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0020_auto_20170908_0257'),
    ]

    operations = [
        migrations.AddField(
            model_name='idpprofile',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2017, 10, 3, 14, 16, 34, 743365, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='idpprofile',
            name='primary',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='idpprofile',
            name='updated',
            field=models.DateTimeField(default=datetime.datetime(2017, 10, 3, 14, 16, 38, 392655, tzinfo=utc), auto_now=True),
            preserve_default=False,
        ),
    ]
