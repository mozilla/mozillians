from django.db.models import Count, Manager
from django.db.models.query import QuerySet


class GroupBaseManager(Manager):
    use_for_related_fields = True

    def get_queryset(self):
        from mozillians.groups.models import Group
        qs = super(GroupBaseManager, self).get_queryset()
        if qs.model == Group:
            qs = (qs.filter(groupmembership__status='member').distinct()
                    .annotate(member_count=Count('members')))
        else:
            qs = qs.annotate(member_count=Count('members'))

        return qs


class GroupQuerySet(QuerySet):

    def visible(self):
        return self.filter(visible=True)
