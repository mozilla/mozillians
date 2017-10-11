# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0024_auto_20171011_0320'),
    ]

    operations = [
        migrations.AddField(
            model_name='idpprofile',
            name='email',
            field=models.EmailField(default=b'', max_length=254, blank=True),
        ),
        migrations.AddField(
            model_name='idpprofile',
            name='privacy',
            field=models.PositiveIntegerField(default=3, choices=[(3, 'Mozillians'), (4, 'Public')]),
        ),
        migrations.AlterUniqueTogether(
            name='idpprofile',
            unique_together=set([('profile', 'type', 'email')]),
        ),
    ]
