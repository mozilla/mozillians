from django.db.models import Count, Manager
from django.db.models.query import QuerySet


class GroupBaseManager(Manager):
    use_for_related_fields = True
    queryset_class = QuerySet

    def get_query_set(self):
        qs = self.queryset_class(self.model, using=self._db)
        qs = qs.annotate(member_count=Count('members'))
        return qs

    def __getattr__(self, name):
        return getattr(self.get_query_set(), name)


class GroupQuerySet(QuerySet):

    def visible(self):
        return self.filter(visible=True)


class GroupManager(GroupBaseManager):
    queryset_class = GroupQuerySet
