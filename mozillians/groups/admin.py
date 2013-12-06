from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db.models import Count, Sum

import autocomplete_light

from mozillians.groups.models import (Group, GroupAlias, GroupMembership,
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
        queryset = (queryset.annotate(no_profiles=Count('members')))
        if value:
            return queryset.filter(no_profiles__gt=0)
        return queryset.filter(no_profiles=0)


class CuratedGroupFilter(SimpleListFilter):
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
        return queryset.filter(curator__isnull=value)


class FunctionalAreaFilter(SimpleListFilter):
    """Admin filter for functional areas."""
    title = 'functional_areas'
    parameter_name = 'functional_area'

    def lookups(self, request, model_admin):
        return (('0', 'Not functional area'),
                ('1', 'Functional area'))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        value = self.value() == '1'
        return queryset.filter(functional_area=value)


class VisibleGroupFilter(SimpleListFilter):
    """Admin filter for visible groups."""
    title = 'visible_groups'
    parameter_name = 'visible'

    def lookups(self, request, model_admin):
        return (('0', 'Not visible group'),
                ('1', 'Visible group'))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        value = self.value() == '1'
        return queryset.filter(visible=value)


class GroupBaseEditAdminForm(forms.ModelForm):
    merge_with = forms.ModelMultipleChoiceField(
        required=False, queryset=None,
        widget=FilteredSelectMultiple('Merge', False))

    def __init__(self, *args, **kwargs):
        queryset = self._meta.model.objects.exclude(pk=kwargs['instance'].id)
        self.base_fields['merge_with'].queryset = queryset
        super(GroupBaseEditAdminForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.instance.merge_groups(self.cleaned_data.get('merge_with', []))
        return super(GroupBaseEditAdminForm, self).save(*args, **kwargs)


class GroupBaseAdmin(admin.ModelAdmin):
    """GroupBase Admin."""
    save_on_top = True
    search_fields = ['name', 'aliases__name', 'url', 'aliases__url']
    list_display = ['name', 'member_count', 'vouched_member_count']
    list_display_links = ['name']
    list_filter = [EmptyGroupFilter]
    readonly_fields = ['url']

    def get_form(self, request, obj=None, **kwargs):
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(kwargs)
        return super(GroupBaseAdmin, self).get_form(request, obj, **defaults)

    def queryset(self, request):
        # The Sum('members__is_vouched') annotation only works for
        # databases where the Boolean type is really an integer. It works
        # for Sqlite3 or MySQL, but fails on Postgres. If Mozillians ever
        # switches from MySQL to a database where this won't work, we'll
        # need to revisit this.
        return (super(GroupBaseAdmin, self)
                .queryset(request)
                .annotate(member_count=Count('members'),
                          vouched_member_count=Sum('members__is_vouched')))

    def member_count(self, obj):
        """Return number of members in group."""
        return obj.member_count
    member_count.admin_order_field = 'member_count'

    def vouched_member_count(self, obj):
        """Return number of vouched members in group"""
        # Annotated field, could be None or a float
        if obj.vouched_member_count:
            return int(obj.vouched_member_count)
        return 0
    vouched_member_count.admin_order_field = 'vouched_member_count'


class GroupAliasInline(admin.StackedInline):
    model = GroupAlias
    readonly_fields = ['name', 'url']


class GroupAddAdminForm(forms.ModelForm):

    class Meta:
        model = Group


class GroupEditAdminForm(GroupBaseEditAdminForm):

    class Meta:
        model = Group


class GroupAdmin(GroupBaseAdmin):
    """Group Admin."""
    form = autocomplete_light.modelform_factory(Group, form=GroupEditAdminForm)
    add_form = autocomplete_light.modelform_factory(Group,
                                                    form=GroupAddAdminForm)
    inlines = [GroupAliasInline]
    list_display = ['name', 'curator', 'wiki', 'website', 'irc_channel',
                    'functional_area', 'accepting_new_members', 'members_can_leave', 'visible',
                    'member_count', 'vouched_member_count']
    list_filter = [CuratedGroupFilter, EmptyGroupFilter, FunctionalAreaFilter, VisibleGroupFilter]


class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ['group', 'userprofile']


class SkillAliasInline(admin.StackedInline):
    model = SkillAlias


class SkillAddAdminForm(forms.ModelForm):

    class Meta:
        model = Skill


class SkillEditAdminForm(GroupBaseEditAdminForm):

    class Meta:
        model = Skill


class SkillAdmin(GroupBaseAdmin):
    form = SkillEditAdminForm
    add_form = SkillAddAdminForm
    inlines = [SkillAliasInline]


class LanguageAliasInline(admin.StackedInline):
    model = LanguageAlias


class LanguageAddAdminForm(forms.ModelForm):

    class Meta:
        model = Language


class LanguageEditAdminForm(GroupBaseEditAdminForm):

    class Meta:
        model = Language


class LanguageAdmin(GroupBaseAdmin):
    form = LanguageEditAdminForm
    add_form = LanguageAddAdminForm
    inlines = [LanguageAliasInline]

admin.site.register(Group, GroupAdmin)
admin.site.register(GroupMembership, GroupMembershipAdmin)
admin.site.register(Language, LanguageAdmin)
admin.site.register(Skill, SkillAdmin)
