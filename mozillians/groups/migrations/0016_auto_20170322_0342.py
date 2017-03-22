# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import autoslug.fields
import mozillians.groups.templatetags.helpers


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0015_groupmembership_needs_renewal'),
    ]

    operations = [
        migrations.AlterField(
            model_name='groupalias',
            name='url',
            field=autoslug.fields.AutoSlugField(editable=False, populate_from=b'name', blank=True, unique=True, slugify=mozillians.groups.templatetags.helpers.slugify),
        ),
        migrations.AlterField(
            model_name='skillalias',
            name='url',
            field=autoslug.fields.AutoSlugField(editable=False, populate_from=b'name', blank=True, unique=True, slugify=mozillians.groups.templatetags.helpers.slugify),
        ),
    ]
