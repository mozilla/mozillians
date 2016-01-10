# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import operator
from datetime import datetime

from django.db import models, migrations
from django.conf import settings


def vouch_mozilla_alternate_emails(apps, schema_editor):
    """Vouch all users with a mozilla* email address as alternate."""
    ExternalAccount = apps.get_model('users', 'ExternalAccount')
    UserProfile = apps.get_model('users', 'UserProfile')

    email_query = reduce(operator.or_,
                         (models.Q(identifier__icontains=item)
                          for item in settings.AUTO_VOUCH_DOMAINS))
    user_ids = (ExternalAccount.objects.filter(type='EMAIL').filter(email_query)
                .values_list('user_id', flat=True).distinct())
    users = UserProfile.objects.filter(id__in=user_ids)

    q_args = {
        'autovouch': True,
        'description': settings.AUTO_VOUCH_REASON
    }
    for user in users:
        if not user.vouches_received.filter(**q_args).exists():
            if not user.vouches_received.all().count() >= settings.VOUCH_COUNT_LIMIT:
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


def unvouch_mozilla_alternate_emails(apps, schema_editor):
    """Vouches cannot be removed, do nothing please."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20150827_0822'),
    ]

    operations = [
        migrations.RunPython(vouch_mozilla_alternate_emails, unvouch_mozilla_alternate_emails)
    ]
