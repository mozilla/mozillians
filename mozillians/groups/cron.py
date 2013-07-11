from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Count

import commonware.log
import cronjobs

from mozillians.groups.models import AUTO_COMPLETE_COUNT, Group, Skill, Language


log = commonware.log.getLogger('m.cron')


@cronjobs.register
def assign_autocomplete_to_groups():
    """Hourly job to assign autocomplete status to Mozillian popular
    groups, languages, and skills.

    """
    # Only assign status to non-system groups.
    # TODO: add stats.d timer here
    for g in (Group.objects.filter(always_auto_complete=False, system=False)
                           .annotate(count=Count('members'))):
        g.auto_complete = g.count > AUTO_COMPLETE_COUNT
        g.save()

    # Assign appropriate status to skills
    for g in (Skill.objects.filter(always_auto_complete=False)
                           .annotate(count=Count('members'))):
        g.auto_complete = g.count > AUTO_COMPLETE_COUNT
        g.save()

    # Assign appropriate status to languages spoken
    for g in (Language.objects.filter(always_auto_complete=False)
                              .annotate(count=Count('members'))):
        g.auto_complete = g.count > AUTO_COMPLETE_COUNT
        g.save()
