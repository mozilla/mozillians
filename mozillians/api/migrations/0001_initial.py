# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import mozillians.users.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='APIApp',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('description', models.TextField()),
                ('url', models.URLField(default=b'', max_length=300, blank=True)),
                ('key', models.CharField(default=b'', help_text=b'Leave this field empty to generate a new API key.', max_length=256, blank=True)),
                ('is_mozilla_app', models.BooleanField(default=False)),
                ('is_active', models.BooleanField(default=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'APIv1 App',
                'verbose_name_plural': 'APIv1 Apps',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='APIv2App',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('enabled', models.BooleanField(default=False)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('description', models.TextField()),
                ('url', models.URLField(default=b'', max_length=300, blank=True)),
                ('key', models.CharField(default=b'', help_text=b'Leave this field empty to generate a new API key.', unique=True, max_length=255, blank=True)),
                ('privacy_level', mozillians.users.models.PrivacyField(default=4, choices=[(1, 'Privileged'), (3, 'Mozillians'), (4, 'Public')])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('last_used', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'APIv2 App',
                'verbose_name_plural': 'APIv2 Apps',
            },
            bases=(models.Model,),
        ),
    ]
