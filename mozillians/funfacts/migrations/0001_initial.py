# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import mozillians.funfacts.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FunFact',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=255)),
                ('published', models.BooleanField(default=False, choices=[(True, b'Published'), (False, b'Unpublished')])),
                ('public_text', models.TextField()),
                ('number', models.TextField(max_length=1000, validators=[mozillians.funfacts.models._validate_query])),
                ('divisor', models.TextField(blank=True, max_length=1000, null=True, validators=[mozillians.funfacts.models._validate_query])),
            ],
            options={
                'ordering': ['created'],
            },
            bases=(models.Model,),
        ),
    ]
