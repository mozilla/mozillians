# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import sorl.thumbnail.fields
import mozillians.announcements.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Announcement',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('title', models.CharField(max_length=255)),
                ('text', models.TextField(max_length=750)),
                ('image', sorl.thumbnail.fields.ImageField(default=b'', help_text=b'60x60 pixel image recommended. Image will be rescaled automatically to a square.', upload_to=mozillians.announcements.models._calculate_image_filename, blank=True)),
                ('publish_from', models.DateTimeField(help_text=b'Timezone is America/Los_Angeles')),
                ('publish_until', models.DateTimeField(help_text=b'Timezone is America/Los_Angeles', null=True, blank=True)),
            ],
            options={
                'ordering': ['-publish_from'],
                'get_latest_by': 'publish_from',
            },
            bases=(models.Model,),
        ),
    ]
