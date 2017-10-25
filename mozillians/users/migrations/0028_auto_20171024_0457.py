# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import mozillians.users.models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0027_auto_20171020_0416'),
    ]

    operations = [
        migrations.AddField(
            model_name='idpprofile',
            name='primary_contact_identity',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='privacy_idp_profile',
            field=mozillians.users.models.PrivacyField(default=3, choices=[(3, 'Mozillians'), (4, 'Public'), (1, 'Private')]),
        ),
        migrations.AlterField(
            model_name='externalaccount',
            name='privacy',
            field=models.PositiveIntegerField(default=3, choices=[(3, 'Mozillians'), (4, 'Public'), (1, 'Private')]),
        ),
        migrations.AlterField(
            model_name='idpprofile',
            name='privacy',
            field=models.PositiveIntegerField(default=3, choices=[(3, 'Mozillians'), (4, 'Public'), (1, 'Private')]),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='privacy_email',
            field=mozillians.users.models.PrivacyField(default=3, choices=[(3, 'Mozillians'), (4, 'Public'), (1, 'Private')]),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='privacy_tshirt',
            field=mozillians.users.models.PrivacyField(default=1, choices=[(1, 'Private')]),
        ),
    ]
