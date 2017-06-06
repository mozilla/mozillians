from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.urlresolvers import reverse
from django.db.models import Count
from django.utils.html import escape
from django.utils.safestring import mark_safe

from dal import autocomplete
from import_export.fields import Field
from import_export.resources import ModelResource

from mozillians.common.mixins import MozilliansAdminExportMixin
from mozillians.groups.models import (Group, GroupAlias, GroupMembership,
                                      Invite, Skill, SkillAlias)
from mozillians.phonebook.admin import RedeemedInviteFilter


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
        return queryset.filter(curators__isnull=value)


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


class InvalidateGroupFilter(SimpleListFilter):
    """Admin filter for groups that can expire."""
    title = 'Group Expiration'
    parameter_name = 'expires'

    def lookups(self, request, model_admin):
        return (('0', 'Group does not expire'),
                ('1', 'Group expires'),)

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        if self.value() == '1':
            return queryset.filter(invalidation_days__isnull=False)
        return queryset.filter(invalidation_days__isnull=True)


class NeedsRenewalFilter(SimpleListFilter):
    title = 'Needs Renewal'
    parameter_name = 'needs_renewal'

    def lookups(self, request, model_admin):
        return (('True', 'Needs Renewal'),
                ('False', 'Does not need renewal'),)

    def queryset(self, request, queryset):
        if self.value() == 'True':
            return queryset.filter(needs_renewal=True)
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


class GroupBaseAdmin(MozilliansAdminExportMixin, admin.ModelAdmin):
    """GroupBase Admin."""
    save_on_top = True
    search_fields = ['name', 'aliases__name', 'url', 'aliases__url']
    list_display = ['name', 'total_member_count']
    list_display_links = ['name']
    list_filter = [EmptyGroupFilter, NoURLFilter]
    readonly_fields = ['url', 'total_member_count']

    def get_form(self, request, obj=None, **kwargs):
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(kwargs)
        return super(GroupBaseAdmin, self).get_form(request, obj, **defaults)

    def total_member_count(self, obj):
        """Return total number of members in group.

        Do not use annonated value member_count directly (bug 908053).
        """
        return obj.members.count()
    total_member_count.admin_order_field = 'member_count'

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
        fields = '__all__'
        widgets = {
            'curators': autocomplete.ModelSelect2Multiple(url='users:vouched-autocomplete')
        }


class GroupEditAdminForm(GroupBaseEditAdminForm):

    class Meta:
        model = Group
        fields = '__all__'
        widgets = {
            'curators': autocomplete.ModelSelect2Multiple(url='users:vouched-autocomplete'),
        }


class InviteInline(admin.StackedInline):
    model = Invite
    extra = 0


class GroupAdmin(GroupBaseAdmin):
    """Group Admin."""
    form = GroupEditAdminForm
    add_form = GroupAddAdminForm
    inlines = [GroupAliasInline]
    list_display = ['name', 'get_curators', 'get_invites', 'functional_area',
                    'accepting_new_members', 'members_can_leave', 'visible', 'total_member_count',
                    'full_member_count', 'pending_member_count', 'pending_terms_member_count']
    list_filter = [CuratedGroupFilter, EmptyGroupFilter, FunctionalAreaFilter, VisibleGroupFilter,
                   NoURLFilter, InvalidateGroupFilter]
    readonly_fields = ['url', 'total_member_count', 'full_member_count', 'pending_member_count',
                       'pending_terms_member_count', 'max_reminder']
    search_fields = ('curators__user__username', 'name',)

    fieldsets = (
        ('Group', {
            'fields': ('name', 'url', 'description', 'irc_channel', 'website', 'wiki',
                       'visible', 'terms', 'invalidation_days', 'invite_email_text',)
        }),
        ('Functional Area', {
            'fields': ('functional_area', 'curators',)
        }),
        ('Membership', {
            'fields': (('accepting_new_members', 'new_member_criteria',),
                       'members_can_leave',
                       ('total_member_count', 'full_member_count', 'pending_member_count',
                        'pending_terms_member_count',),)
        }),
        ('Debug info', {
            'fields': ('max_reminder',),
            'classes': ('collapse',)
        }),
    )

    def get_form(self, request, obj=None, **kwargs):
        """Conditionally update the fieldset to include the 'merge_with' field."""

        # If there is an object, then it's about editing a group.
        if obj:
            self.fieldsets[0][1]['fields'] += ('merge_with',)
        return super(GroupAdmin, self).get_form(request, obj, **kwargs)

    def full_member_count(self, obj):
        """Return number of members in group."""
        return obj.groupmembership_set.filter(status=GroupMembership.MEMBER).count()

    def pending_member_count(self, obj):
        """Return number of pending members in group."""
        return obj.groupmembership_set.filter(status=GroupMembership.PENDING).count()

    def pending_terms_member_count(self, obj):
        """Return number of members in group who haven't accepted terms yet."""
        return obj.groupmembership_set.filter(status=GroupMembership.PENDING_TERMS).count()

    def get_curators(self, obj):
        url = u"<a href='{0}'>{1}</a>"
        profile_urls = [url.format(reverse('admin:users_userprofile_change', args=[profile.id]),
                                   escape(profile.full_name))
                        for profile in obj.curators.all()]
        return mark_safe(', '.join(profile_urls))
    get_curators.short_description = 'Curators'

    def get_invites(self, obj):
        url = u"<a href='{0}'>{1}</a>"
        profile_urls = [url.format(reverse('admin:users_userprofile_change', args=[profile.id]),
                                   escape(profile.full_name))
                        for profile in obj.invites.all()]
        return mark_safe(', '.join(profile_urls))
    get_invites.short_description = 'Invites'


class GroupMembershipResource(ModelResource):
    """django-import-export Groupmembership Resource."""
    username = Field(attribute='userprofile__user__username')
    group_name = Field(attribute='group__name')

    class Meta:
        model = GroupMembership


class BaseGroupMembershipAutocompleteForm(forms.ModelForm):

    class Meta:
        model = GroupMembership
        fields = '__all__'
        widgets = {
            'userprofile': autocomplete.ModelSelect2(url='users:vouched-autocomplete'),
            'group': autocomplete.ModelSelect2(url='groups:group-autocomplete')
        }


class GroupMembershipAdmin(MozilliansAdminExportMixin, admin.ModelAdmin):
    resource_class = GroupMembershipResource
    list_display = ['group', 'userprofile', 'status', 'date_joined', 'updated_on']
    search_fields = [
        'group__name', 'group__url', 'group__description', 'group__aliases__name',
        'group__aliases__url', 'userprofile__full_name', 'userprofile__ircname',
        'userprofile__user__username', 'userprofile__user__email'
    ]
    list_filter = (
        NeedsRenewalFilter,
        ('updated_on', admin.DateFieldListFilter,),
        'status',
    )
    form = BaseGroupMembershipAutocompleteForm


class SkillAliasInline(admin.StackedInline):
    model = SkillAlias


class SkillAddAdminForm(forms.ModelForm):

    class Meta:
        model = Skill
        fields = '__all__'


class SkillEditAdminForm(GroupBaseEditAdminForm):

    class Meta:
        model = Skill
        fields = '__all__'


class SkillAdmin(GroupBaseAdmin):
    form = SkillEditAdminForm
    add_form = SkillAddAdminForm
    inlines = [SkillAliasInline]


class InviteAutocompleteForm(forms.ModelForm):

    class Meta:
        model = Invite
        fields = ('__all__')
        widgets = {
            'inviter': autocomplete.ModelSelect2(url='users:vouched-autocomplete'),
            'redeemer': autocomplete.ModelSelect2(url='users:vouched-autocomplete'),
            'group': autocomplete.ModelSelect2(url='groups:group-autocomplete')
        }


class InviteResource(ModelResource):
    inviter = Field(attribute='inviter__full_name')
    redeemer = Field(attribute='redeemer__full_name')
    group = Field(attribute='group__name')

    class Meta:
        fields = ['inviter', 'redeemer', 'group', 'accepted', 'created', 'updated']
        model = Invite


class InviteAdmin(MozilliansAdminExportMixin, admin.ModelAdmin):
    resource_class = InviteResource
    search_fields = ['inviter__full_name', 'redeemer__full_name', 'group__name']
    list_display = ['inviter', 'redeemer', 'group', 'created', 'updated']
    readonly_fields = ['created', 'updated']
    list_filter = [RedeemedInviteFilter]
    form = InviteAutocompleteForm


admin.site.register(Group, GroupAdmin)
admin.site.register(GroupMembership, GroupMembershipAdmin)
admin.site.register(Skill, SkillAdmin)
admin.site.register(Invite, InviteAdmin)
