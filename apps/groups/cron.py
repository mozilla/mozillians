from django.db.models import Count

import commonware.log
import cronjobs

from groups.models import AUTO_COMPLETE_COUNT, Group


log = commonware.log.getLogger('m.cron')


@cronjobs.register
def assign_autocomplete_to_groups():
    """Hourly job to assign autocomplete status to popular Mozillian groups."""
    # Only assign status to non-system groups.
    # TODO: add stats.d timer here
    for g in (Group.objects.filter(always_auto_complete=False, system=False)
                           .annotate(count=Count('userprofile'))):
        g.auto_complete = g.count > AUTO_COMPLETE_COUNT
        g.save()
