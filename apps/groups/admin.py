from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db.models import Count

import utils
from models import (Group, GroupAlias,
                    Language, LanguageAlias,
                    Skill, SkillAlias)


class EmptyGroupFilter(SimpleListFilter):
    title = 'empty_group'
    parameter_name = 'empty_group'

    def lookups(self, request, model_admin):
        return (('False', 'Empty'),
                ('True', 'Not empty'))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        value = self.value() == 'True'
        queryset = (queryset.annotate(no_profiles=Count('userprofile')))
        if value:
            return queryset.filter(no_profiles__gt=0)
        return queryset.filter(no_profiles=0)


class EmptyGroupFilter(SimpleListFilter):
    title = 'empty_group'
    parameter_name = 'empty_group'

    def lookups(self, request, model_admin):
        return (('False', 'Empty'),
                ('True', 'Not empty'))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        value = self.value() == 'True'
        queryset = (queryset.annotate(no_profiles=Count('userprofile')))
        if value:
                 return queryset.filter(no_profiles__gt=0)
        return queryset.filter(no_profiles=0)


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
    save_on_top = True
    search_fields = ['name']
    list_display = ['name', 'no_members']
    list_display_links = ['name']
    list_filter = [EmptyGroupFilter]

    def queryset(self, request):
        return (super(GroupBaseAdmin, self)
                .queryset(request).annotate(no_members=Count('userprofile')))

    def no_members(self, obj):
        """Return number of members in group."""
        return obj.no_members
    no_members.admin_order_field = 'no_members'


class GroupAliasInline(admin.StackedInline):
    model = GroupAlias


class GroupAdminForm(forms.ModelForm):
    merge_with_groups = forms.ModelMultipleChoiceField(
        required=False, queryset = None,
        widget=FilteredSelectMultiple('Merge', False))

    def __init__(self, *args, **kwargs):
        model= Group
        if 'instance' in kwargs:
            queryset = model.objects.exclude(pk=kwargs['instance'].id)
            self.base_fields['merge_with_groups'].queryset = queryset
        else:
            self.declared_fields.pop('merge_with_groups')
        super(GroupAdminForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        utils.merge_groups(self.instance,
                           self.cleaned_data.get('merge_with_groups', []))
        return super(GroupAdminForm, self).save(*args, **kwargs)

    class Meta:
        model = Group


class GroupAdmin(GroupBaseAdmin):
    """Group Admin."""
    form = GroupAdminForm
    inlines = [GroupAliasInline]
    list_display = ['name', 'steward', 'wiki', 'website', 'irc_channel',
                    'no_members']
    raw_id_fields = ['steward']
    list_filter = [CurratedGroupFilter, EmptyGroupFilter]


class SkillAliasInline(admin.StackedInline):
    model = SkillAlias

class SkillAdmin(GroupBaseAdmin):
    inlines = [SkillAliasInline]

class LanguageAliasInline(admin.StackedInline):
    model = LanguageAlias

class LanguageAdmin(GroupBaseAdmin):
    inlines = [LanguageAliasInline]

class SkillAliasInline(admin.StackedInline):
    model = SkillAlias


class SkillAdmin(GroupBaseAdmin):
    inlines = [SkillAliasInline]


class LanguageAliasInline(admin.StackedInline):
    model = LanguageAlias


class LanguageAdmin(GroupBaseAdmin):
    inlines = [LanguageAliasInline]


admin.site.register(Group, GroupAdmin)
admin.site.register(Language, LanguageAdmin)
admin.site.register(Skill, SkillAdmin)
