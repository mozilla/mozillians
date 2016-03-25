# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0013_auto_20160323_0228'),
    ]

    operations = [
        migrations.AddField(
            model_name='group',
            name='invite_email_text',
            field=models.TextField(default=b'', help_text='Please enter any additional text for the invitation email', max_length=2048, blank=True),
        ),
    ]
