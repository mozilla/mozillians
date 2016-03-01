from django.db.models import Count, Manager
from django.db.models.query import QuerySet


class GroupBaseManager(Manager):
    use_for_related_fields = True

    def get_queryset(self):
        qs = super(GroupBaseManager, self).get_queryset()
        qs = qs.annotate(member_count=Count('members'))
        return qs


class GroupQuerySet(QuerySet):

    def visible(self):
        return self.filter(visible=True)
