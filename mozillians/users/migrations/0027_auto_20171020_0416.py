# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0026_auto_20171016_0340'),
    ]

    operations = [
        migrations.AlterField(
            model_name='idpprofile',
            name='type',
            field=models.IntegerField(default=None, null=True, choices=[(30, b'Github Provider'), (40, b'LDAP Provider'), (10, b'Passwordless Provider'), (20, b'Google Provider')]),
        ),
    ]
