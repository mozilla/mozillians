from django.db.models import Count

from celery.task import task

from mozillians.groups.models import AUTO_COMPLETE_COUNT, Group, Language, Skill


@task
def assign_autocomplete_to_groups():
    """Set auto_complete to True when member count is larger than
    AUTO_COMPLETE_COUNT.

    Note: no_members includes both vouched and unvouched users ATM. We
    should count only vouched users.

    """
    for model in [Group, Language, Skill]:
        groups = (model.objects
                 .filter(always_auto_complete=False)
                 .annotate(no_members=Count('members'))
                 .filter(no_members__gte=AUTO_COMPLETE_COUNT))
        if isinstance(model, Group):
            groups = groups.filter(system=False)

        model.objects.update(auto_complete=False)
        # Conveting the ValuesListQuerySet to list is required to
        # avoid mysql refusing to update the same tables used in the
        # SELECT part.
        (model.objects
         .filter(pk__in=list(groups.values_list('id', flat=True)))
         .update(auto_complete=True))

@task
def remove_empty_groups():
    """Remove empty groups."""
    for model in [Group, Skill]:
        (model.objects
         .annotate(mcount=Count('members')).filter(mcount=0).delete())
