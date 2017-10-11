# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def forwards(apps, schema_editor):
    """Forwards data migration.

    Remove all the externalaccounts for
    GitHub, GTalk, Verbatim and Locamotion.
    """
    ExternalAccount = apps.get_model('users', 'ExternalAccount')
    ExternalAccount.objects.filter(type='GITHUB').delete()
    ExternalAccount.objects.filter(type='GTALK').delete()
    ExternalAccount.objects.filter(type='MOZILLALOCAMOTION').delete()
    ExternalAccount.objects.filter(type='MOZILLAVERBATIM').delete()


def backwards(apps, schema_editor):
    """Backwards migration.

    Do nothing please.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0021_auto_20171003_0716'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards)
    ]
