from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from models import Group


class CurratedGroupFilter(SimpleListFilter):
    """Admin filter for curated groups."""
    title = 'curated'
    parameter_name = 'curated'

    def lookups(self, request, model_admin):
        return (('False', 'Curated'),
                ('True', 'Not curated'))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        value = self.value() == 'True'
        return queryset.filter(steward__isnull=value)


class GroupAdmin(admin.ModelAdmin):
    """Group Admin."""
    list_display = ['name', 'steward', 'wiki', 'website', 'irc_channel',
                    'no_members']
    search_fields = ['name']
    raw_id_fields = ['steward']
    list_filter = [CurratedGroupFilter]

    def no_members(self, obj):
        """Return number of members in group."""
        return obj.userprofile_set.count()

admin.site.register(Group, GroupAdmin)
