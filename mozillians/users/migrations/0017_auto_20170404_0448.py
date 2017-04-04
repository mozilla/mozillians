# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from django.db import migrations
from django.conf import settings


def autovouch_getpocket(apps, schema_editor):
    """Vouch all users with a getpocket email."""

    UserProfile = apps.get_model('users', 'UserProfile')
    ExternalAccount = apps.get_model('users', 'ExternalAccount')

    primary_qs_list = UserProfile.objects.filter(
        user__email__endswith='@getpocket.com',
    ).values_list('id', flat=True)

    alternate_qs_list = ExternalAccount.objects.filter(
        type='EMAIL',
        identifier__endswith='@getpocket.com'
    ).values_list('user__id', flat=True)

    unique_ids = set(list(primary_qs_list) + list(alternate_qs_list))

    userprofile_qs = UserProfile.objects.filter(pk__in=unique_ids)

    q_args = {
        'autovouch': True,
        'description': settings.AUTO_VOUCH_REASON
    }

    for user in userprofile_qs:
        already_autovouched = user.vouches_received.filter(**q_args).exists()
        reached_max_vouches = user.vouches_received.all().count() >= settings.VOUCH_COUNT_LIMIT
        if not already_autovouched and not reached_max_vouches:
            user.vouches_received.create(
                voucher=None,
                date=datetime.now(),
                description=settings.AUTO_VOUCH_REASON,
                autovouch=True
            )
            vouches = user.vouches_received.all().count()
            user.is_vouched = vouches > 0
            user.can_vouch = vouches > settings.CAN_VOUCH_THRESHOLD
            user.save()


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0016_auto_20170331_0812'),
    ]

    operations = [
        migrations.RunPython(autovouch_getpocket, backwards),
    ]
