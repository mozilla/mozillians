# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('funfacts', '0002_auto_20180103_0608'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='funfact',
            options={'ordering': ['created']},
        ),
    ]
