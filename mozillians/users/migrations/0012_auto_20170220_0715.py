# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import mozillians.users.models


class Migration(migrations.Migration):

    dependencies = [
        ('cities_light', '0006_compensate_for_0003_bytestring_bug'),
        ('users', '0011_remove_userprofile_is_spam'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='city',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='cities_light.City', null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='country',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='cities_light.Country', null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='privacy_city',
            field=mozillians.users.models.PrivacyField(default=3, choices=[(3, 'Mozillians'), (4, 'Public')]),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='privacy_country',
            field=mozillians.users.models.PrivacyField(default=3, choices=[(3, 'Mozillians'), (4, 'Public')]),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='privacy_region',
            field=mozillians.users.models.PrivacyField(default=3, choices=[(3, 'Mozillians'), (4, 'Public')]),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='region',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='cities_light.Region', null=True),
        ),
    ]
