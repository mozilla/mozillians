from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.views.main import ChangeList
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db.models import Count, Sum

import autocomplete_light

from mozillians.groups.models import (Group, GroupAlias, GroupMembership,
                                      Skill, SkillAlias)


class EmptyGroupFilter(SimpleListFilter):
    title = 'utilization'
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
    title = 'functional area'
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
    title = 'visibility'
    parameter_name = 'visible'

    def lookups(self, request, model_admin):
        return (('0', 'Not visible group'),
                ('1', 'Visible group'))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        value = self.value() == '1'
        return queryset.filter(visible=value)


class NoURLFilter(SimpleListFilter):
    """Admin filter for groups without a url."""
    title = 'no URL'
    parameter_name = 'empty_url'

    def lookups(self, request, model_admin):
        return (('True', 'No URL'),)

    def queryset(self, request, queryset):
        if self.value() == 'True':
            return queryset.filter(url='')
        return queryset


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


class GroupBaseChangeList(ChangeList):
    # We can't just override queryset() on the ModelAdmin class because the
    # changelist applies search and filtering on top of whatever that returns,
    # and we need to apply our annotations after that.  So we
    # need to subclass the changelist itself.
    def get_query_set(self, request):
        qset = super(GroupBaseChangeList, self).get_query_set(request)

        # HACK: we want to annotate the result, but if a group has matched a search
        # in more than one way, the annotations end up double-counting members. So
        # execute the query to get the final set of groups, then generate a new,
        # simple query that just includes those groups and annotate that.
        qset = qset.order_by()  # (No point in wasting cycles sorting these results)
        pks = qset.values_list('pk', flat=True)
        qset = Group.objects.filter(pk__in=pks)

        # Restore ordering.
        qset = qset.order_by(*self.get_ordering(request, qset))

        # Also note:
        # The Sum('members__is_vouched') annotation only works for
        # databases where the Boolean type is really an integer. It works
        # for Sqlite3 or MySQL, but fails on Postgres. If Mozillians ever
        # switches from MySQL to a database where this won't work, we'll
        # need to revisit this.
        return qset.annotate(member_count=Count('members'),
                             vouched_member_count=Sum('members__is_vouched'))


class GroupBaseAdmin(admin.ModelAdmin):
    """GroupBase Admin."""
    save_on_top = True
    search_fields = ['name', 'aliases__name', 'url', 'aliases__url']
    list_display = ['name', 'member_count', 'vouched_member_count']
    list_display_links = ['name']
    list_filter = [EmptyGroupFilter, NoURLFilter]
    readonly_fields = ['url']

    def get_form(self, request, obj=None, **kwargs):
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(kwargs)
        return super(GroupBaseAdmin, self).get_form(request, obj, **defaults)

    def get_changelist(self, request, **kwargs):
        return GroupBaseChangeList

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

    class Media:
        css = {
            'all': ('mozillians/css/admin.css',)
        }


class GroupAliasInline(admin.StackedInline):
    model = GroupAlias
    readonly_fields = ['name', 'url']


class GroupAddAdminForm(forms.ModelForm):

    class Meta:
        model = Group


class GroupEditAdminForm(GroupBaseEditAdminForm):

    class Meta:
        model = Group


class GroupMembershipAdminForm(forms.ModelForm):

    class Meta:
        model = GroupMembership
        widgets = {
            # Use autocomplete_light to allow any user profile.
            'userprofile': autocomplete_light.ChoiceWidget('UserProfiles'),
            'group': autocomplete_light.ChoiceWidget('Groups'),
        }


class GroupAdmin(GroupBaseAdmin):
    """Group Admin."""
    form = autocomplete_light.modelform_factory(Group, form=GroupEditAdminForm)
    add_form = autocomplete_light.modelform_factory(Group,
                                                    form=GroupAddAdminForm)
    inlines = [GroupAliasInline]
    list_display = ['name', 'curator', 'functional_area', 'accepting_new_members',
                    'members_can_leave', 'visible', 'member_count', 'vouched_member_count']
    list_filter = [CuratedGroupFilter, EmptyGroupFilter, FunctionalAreaFilter, VisibleGroupFilter,
                   NoURLFilter]


class GroupMembershipAdmin(admin.ModelAdmin):
    list_display = ['group', 'userprofile']
    search_fields = ['group__name', 'group__url', 'group__description',
                     'group__aliases__name', 'group__aliases__url',
                     'userprofile__full_name', 'userprofile__ircname',
                     'userprofile__region', 'userprofile__city', 'userprofile__country',
                     'userprofile__user__username', 'userprofile__user__email'
                     ]
    form = GroupMembershipAdminForm


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


admin.site.register(Group, GroupAdmin)
admin.site.register(GroupMembership, GroupMembershipAdmin)
admin.site.register(Skill, SkillAdmin)
