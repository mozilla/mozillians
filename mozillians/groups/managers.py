from django.db.models import Case, Count, IntegerField, Manager, Sum, When
from django.db.models.query import QuerySet


class GroupBaseManager(Manager):
    use_for_related_fields = True

    def get_queryset(self):
        """Annotate count of group members."""
        qs = super(GroupBaseManager, self).get_queryset()
        qs = qs.annotate(member_count=Count('members'))
        return qs


class GroupManager(Manager):
    use_for_related_fields = True

    def get_queryset(self):
        """Annotate count of memberships of type MEMBER."""

        from mozillians.groups.models import GroupMembership

        qs = super(GroupManager, self).get_queryset()
        annotation = Sum(
            Case(
                When(
                    groupmembership__status=GroupMembership.MEMBER,
                    then=1
                ),
                default=0, output_field=IntegerField()
            )
        )
        qs = qs.annotate(member_count=annotation)
        return qs


class GroupQuerySet(QuerySet):

    def visible(self):
        return self.filter(visible=True)
