# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def forward_migrate_group_curators(apps, schema_editor):
    """Migrate forwards all the data for the ForeignKey curator
    to the m2m field curators.
    """
    Group = apps.get_model('groups', 'Group')

    for group in Group.objects.all():
        if group.curator:
            group.curators.add(group.curator)
            group.save()


def backward_migrate_group_curators(apps, schema_editor):
    """Do nothing please."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0007_group_curators'),
    ]

    operations = [
        migrations.RunPython(forward_migrate_group_curators,
                             backward_migrate_group_curators),
    ]
