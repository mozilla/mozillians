from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db.models import Count

import autocomplete_light

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


class GroupBaseEditAdminForm(forms.ModelForm):
    merge_with = forms.ModelMultipleChoiceField(
        required=False, queryset = None,
        widget=FilteredSelectMultiple('Merge', False))

    def __init__(self, *args, **kwargs):
        queryset = self._meta.model.objects.exclude(pk=kwargs['instance'].id)
        self.base_fields['merge_with'].queryset = queryset
        super(GroupBaseEditAdminForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        utils.merge_groups(self.instance,
                           self.cleaned_data.get('merge_with', []))
        return super(GroupBaseEditAdminForm, self).save(*args, **kwargs)


class GroupBaseAdmin(admin.ModelAdmin):
    """GroupBase Admin."""
    save_on_top = True
    search_fields = ['name', 'aliases__name']
    list_display = ['name', 'member_count']
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
        return (super(GroupBaseAdmin, self)
                .queryset(request).annotate(member_count=Count('userprofile')))

    def member_count(self, obj):
        """Return number of members in group."""
        return obj.member_count
    member_count.admin_order_field = 'member_count'


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
    list_display = ['name', 'steward', 'wiki', 'website', 'irc_channel',
                    'member_count']
    list_filter = [CurratedGroupFilter, EmptyGroupFilter]


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
admin.site.register(Language, LanguageAdmin)
admin.site.register(Skill, SkillAdmin)
