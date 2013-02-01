from django.contrib import admin
from django.contrib.admin import SimpleListFilter

import utils
from models import (Group, GroupAlias,
                    Language, LanguageAlias,
                    Skill, SkillAlias)


def merge_groups_action():
    """Merge groups admin action."""
    def merge_groups(modeladmin, request, queryset):
        master_group = queryset[0]
        groups = queryset[1:]
        utils.merge_groups(master_group, groups)
    merge_groups.short_description = 'Merge selected groups'
    return merge_groups


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


class GroupBaseAdmin(admin.ModelAdmin):
    """GroupBase Admin."""
    list_display = ['id', 'name', 'no_members']
    list_display_links = ['id', 'name']
    actions = [merge_groups_action()]

    def no_members(self, obj):
        """Return number of members in group."""
        return obj.userprofile_set.count()


class GroupAdmin(GroupBaseAdmin):
    """Group Admin."""
    list_display = ['id', 'name', 'steward', 'wiki', 'website', 'irc_channel',
                    'no_members']
    search_fields = ['name']
    raw_id_fields = ['steward']
    list_filter = [CurratedGroupFilter]


class GroupAliasBaseAdmin(admin.ModelAdmin):
    """GroupAliasBase Admin."""
    list_display = ['name', 'url', 'alias']
    raw_id_fields = ['alias']


admin.site.register(Group, GroupAdmin)
admin.site.register(Language, GroupBaseAdmin)
admin.site.register(Skill, GroupBaseAdmin)
admin.site.register(GroupAlias, GroupAliasBaseAdmin)
admin.site.register(LanguageAlias, GroupAliasBaseAdmin)
admin.site.register(SkillAlias, GroupAliasBaseAdmin)
