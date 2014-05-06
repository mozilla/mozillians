from django.db.models import Count, Manager


class GroupBaseManager(Manager):
    use_for_related_fields = True

    def get_query_set(self):
        qs = super(GroupBaseManager, self).get_query_set()
        qs = qs.annotate(member_count=Count('members'))
        return qs
