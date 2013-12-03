"""Lookup code for groups for django-selectable"""
from selectable.base import ModelLookup
from selectable.decorators import ajax_required
from selectable.registry import registry

from mozillians.groups.models import Group


@ajax_required
class GroupLookup(ModelLookup):
    model = Group
    search_fields = ('name__icontains',)

    def get_item_id(self, group):
        return group.name.lower()

    def get_item(self, group_name):
        try:
            return Group.objects.get(name__iexact=group_name)
        except Group.DoesNotExist:
            return None
        except Group.MultipleObjectsReturned:
            return Group.objects.filter(name__iexact=group_name)[0]


registry.register(GroupLookup)
