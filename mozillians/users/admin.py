from django import forms
from django.conf import settings
from django.conf.urls import patterns, url
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.models import Group, User
from django.core.urlresolvers import reverse
from django.db.models import Count, Q
from django.forms import ValidationError
from django.http import HttpResponseRedirect

import autocomplete_light
from celery.task.sets import TaskSet
from functools import update_wrapper
from import_export.admin import ExportMixin
from import_export.fields import Field
from import_export.resources import ModelResource
from sorl.thumbnail.admin import AdminImageMixin

import mozillians.users.tasks
from mozillians.common.helpers import get_datetime
from mozillians.groups.models import GroupMembership, Skill
from mozillians.users.cron import index_all_profiles
from mozillians.users.models import (PUBLIC, Language, ExternalAccount, Vouch,
                                     UserProfile, UsernameBlacklist)


admin.site.unregister(Group)


Q_PUBLIC_PROFILES = Q()
for field in UserProfile.privacy_fields():
    key = 'privacy_%s' % field
    Q_PUBLIC_PROFILES |= Q(**{key: PUBLIC})


def subscribe_to_basket_action():
    """Subscribe to Basket action."""

    def subscribe_to_basket(modeladmin, request, queryset):
        """Subscribe to Basket or update details of already subscribed."""
        ts = [(mozillians.users.tasks.update_basket_task
               .subtask(args=[userprofile.id]))
              for userprofile in queryset]
        TaskSet(ts).apply_async()
        messages.success(request, 'Basket update started.')
    subscribe_to_basket.short_description = 'Subscribe to or Update Basket'
    return subscribe_to_basket


def unsubscribe_from_basket_action():
    """Unsubscribe from Basket action."""

    def unsubscribe_from_basket(modeladmin, request, queryset):
        """Unsubscribe from Basket."""
        ts = [(mozillians.users.tasks.remove_from_basket_task
               .subtask(args=[userprofile.user.email, userprofile.basket_token]))
              for userprofile in queryset]
        TaskSet(ts).apply_async()
        messages.success(request, 'Basket update started.')
    unsubscribe_from_basket.short_description = 'Unsubscribe from Basket'

    return unsubscribe_from_basket


def update_can_vouch_action():
    """Update can_vouch flag action."""

    def update_can_vouch(modeladmin, request, queryset):
        for profile in queryset:
            profile.can_vouch = (
                profile.vouches_received.count() >= settings.CAN_VOUCH_THRESHOLD)
            profile.save()
    update_can_vouch.short_description = 'Update can_vouch flag.'
    return update_can_vouch


class SuperUserFilter(SimpleListFilter):
    """Admin filter for superusers."""
    title = 'has access to admin interface'
    parameter_name = 'superuser'

    def lookups(self, request, model_admin):
        return (('False', 'No'),
                ('True', 'Yes'))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        value = self.value() == 'True'
        return queryset.filter(user__is_staff=value)


class PublicProfileFilter(SimpleListFilter):
    """Admin filter for public profiles."""
    title = 'public profile'
    parameter_name = 'public_profile'

    def lookups(self, request, model_admin):
        return (('False', 'No'),
                ('True', 'Yes'))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        if self.value() == 'True':
            return queryset.filter(Q_PUBLIC_PROFILES)

        return queryset.exclude(Q_PUBLIC_PROFILES)


class CompleteProfileFilter(SimpleListFilter):
    """Admin filter for complete profiles."""
    title = 'complete profile'
    parameter_name = 'complete_profile'

    def lookups(self, request, model_admin):
        return (('False', 'Incomplete'),
                ('True', 'Complete'))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        elif self.value() == 'True':
            return queryset.exclude(full_name='')
        else:
            return queryset.filter(full_name='')


class DateJoinedFilter(SimpleListFilter):
    """Admin filter for date joined."""
    title = 'date joined'
    parameter_name = 'date_joined'

    def lookups(self, request, model_admin):

        return map(lambda x: (str(x.year), x.year),
                   User.objects.dates('date_joined', 'year'))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset
        else:
            return queryset.filter(user__date_joined__year=self.value())
        return queryset


class LastLoginFilter(SimpleListFilter):
    """Admin filter for last login."""
    title = 'last login'
    parameter_name = 'last_login'

    def lookups(self, request, model_admin):
        # Number is in days
        return (('<7', 'Less than a week'),
                ('<30', 'Less than a month'),
                ('<90', 'Less than 3 months'),
                ('<180', 'Less than 6 months'),
                ('>180', 'Between 6 and 12 months'),
                ('>360', 'More than a year'))

    def queryset(self, request, queryset):

        if self.value() == '<7':
            return queryset.filter(user__last_login__gte=get_datetime(-7))
        elif self.value() == '<30':
            return queryset.filter(user__last_login__gte=get_datetime(-30))
        elif self.value() == '<90':
            return queryset.filter(user__last_login__gte=get_datetime(-90))
        elif self.value() == '<180':
            return queryset.filter(user__last_login__gte=get_datetime(-180))
        elif self.value() == '>180':
            return queryset.filter(user__last_login__lt=get_datetime(-180),
                                   user__last_login__gt=get_datetime(-360))
        elif self.value() == '>360':
            return queryset.filter(user__last_login__lt=get_datetime(-360))
        return queryset


class LegacyVouchFilter(SimpleListFilter):
    """Admin filter for profiles with new or legacy vouch type."""
    title = 'vouch type'
    parameter_name = 'vouch_type'

    def lookups(self, request, model_admin):
        return (('legacy', 'Legacy'),
                ('new', 'New'))

    def queryset(self, request, queryset):
        vouched = queryset.filter(is_vouched=True)
        newvouches = (Vouch.objects
                      .exclude(description='')
                      .values_list('vouchee', flat=True)
                      .distinct())
        # Load into memory
        newvouches = list(newvouches)

        if self.value() == 'legacy':
            return vouched.exclude(pk__in=newvouches)
        elif self.value() == 'new':
            return vouched.filter(pk__in=newvouches)
        return queryset


class UsernameBlacklistAdmin(ExportMixin, admin.ModelAdmin):
    """UsernameBlacklist Admin."""
    save_on_top = True
    search_fields = ['value']
    list_filter = ['is_regex']
    list_display = ['value', 'is_regex']


admin.site.register(UsernameBlacklist, UsernameBlacklistAdmin)


class LanguageAdmin(ExportMixin, admin.ModelAdmin):
    search_fields = ['userprofile__full_name', 'userprofile__user__email', 'code']
    list_display = ['code', 'userprofile']
    list_filter = ['code']


admin.site.register(Language, LanguageAdmin)


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 1


class GroupMembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 1
    form = autocomplete_light.modelform_factory(GroupMembership)


class LanguageInline(admin.TabularInline):
    model = Language
    extra = 1


class ExternalAccountInline(admin.TabularInline):
    model = ExternalAccount
    extra = 1


class UserProfileAdminForm(forms.ModelForm):
    username = forms.CharField()
    email = forms.CharField()
    last_login = forms.DateTimeField(required=False)
    date_joined = forms.DateTimeField(required=False)

    def __init__(self, *args, **kwargs):
        self.instance = kwargs.get('instance')
        if self.instance:
            self.base_fields['username'].initial = self.instance.user.username
            self.base_fields['email'].initial = self.instance.user.email
        super(UserProfileAdminForm, self).__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data['username']
        if (User.objects.exclude(pk=self.instance.user.pk)
                .filter(username=username).exists()):
            raise ValidationError('Username already exists')
        return username

    def clean_email(self):
        email = self.cleaned_data['email']
        if (User.objects.exclude(pk=self.instance.user.pk)
                .filter(email=email).exists()):
            raise ValidationError('Email already exists')
        return email

    def save(self, *args, **kwargs):
        if self.instance:
            self.instance.user.username = self.cleaned_data.get('username')
            self.instance.user.email = self.cleaned_data.get('email')
            self.instance.user.save()
        return super(UserProfileAdminForm, self).save(*args, **kwargs)

    class Meta:
        model = UserProfile


class UserProfileResource(ModelResource):
    """django-import-export UserProfile Resource."""
    username = Field(attribute='user__username')
    email = Field(attribute='user__email')

    class Meta:
        model = UserProfile


class UserProfileAdmin(AdminImageMixin, ExportMixin, admin.ModelAdmin):
    resource_class = UserProfileResource
    inlines = [LanguageInline, GroupMembershipInline, ExternalAccountInline]
    search_fields = ['full_name', 'user__email', 'user__username', 'ircname',
                     'geo_country__name', 'geo_region__name', 'geo_city__name']
    readonly_fields = ['date_vouched', 'vouched_by', 'user', 'date_joined', 'last_login',
                       'is_vouched', 'can_vouch']
    form = UserProfileAdminForm
    list_filter = ['is_vouched', 'can_vouch', DateJoinedFilter,
                   LastLoginFilter, LegacyVouchFilter, SuperUserFilter,
                   CompleteProfileFilter, PublicProfileFilter, 'externalaccount__type']
    save_on_top = True
    list_display = ['full_name', 'email', 'username', 'geo_country', 'is_vouched', 'can_vouch',
                    'number_of_vouchees']
    list_display_links = ['full_name', 'email', 'username']
    actions = [subscribe_to_basket_action(), unsubscribe_from_basket_action(),
               update_can_vouch_action()]

    fieldsets = (
        ('Account', {
            'fields': ('full_name', 'username', 'email', 'photo',)
        }),
        (None, {
            'fields': ('title', 'bio', 'tshirt', 'ircname', 'date_mozillian',)
        }),
        ('Important dates', {
            'fields': ('date_joined', 'last_login')
        }),
        ('Vouch Info', {
            'fields': ('date_vouched', 'is_vouched', 'can_vouch')
        }),
        ('Location', {
            'fields': ('geo_country', 'geo_region', 'geo_city',
                       'lng', 'lat', 'timezone')
        }),
        ('Services', {
            'fields': ('allows_community_sites', 'allows_mozilla_sites')
        }),
        ('Privacy Settings', {
            'fields': ('privacy_photo', 'privacy_full_name', 'privacy_ircname',
                       'privacy_email', 'privacy_bio',
                       'privacy_geo_city', 'privacy_geo_region', 'privacy_geo_country',
                       'privacy_groups', 'privacy_skills', 'privacy_languages',
                       'privacy_date_mozillian', 'privacy_timezone',
                       'privacy_tshirt', 'privacy_title'),
            'classes': ('collapse',)
        }),
        ('Basket', {
            'fields': ('basket_token',),
            'classes': ('collapse',)
        }),
        ('Skills', {
            'fields': ('skills',)
        }),
    )

    def queryset(self, request):
        qs = super(UserProfileAdmin, self).queryset(request)
        qs = qs.annotate(Count('vouches_made'))
        return qs

    def email(self, obj):
        return obj.user.email
    email.admin_order_field = 'user__email'

    def username(self, obj):
        return obj.user.username
    username.admin_order_field = 'user__username'

    def is_vouched(self, obj):
        return obj.userprofile.is_vouched
    is_vouched.boolean = True
    is_vouched.admin_order_field = 'is_vouched'

    def vouched_by(self, obj):
        voucher = obj.vouched_by
        if voucher:
            voucher_url = reverse('admin:auth_user_change', args=[voucher.id])
            return '<a href="%s">%s</a>' % (voucher_url, voucher)
    vouched_by.admin_order_field = 'vouched_by'
    vouched_by.allow_tags = True

    def number_of_vouchees(self, obj):
        """Return the number of vouchees for obj."""
        return obj.vouches_made.count()
    number_of_vouchees.admin_order_field = 'vouches_made__count'

    def last_login(self, obj):
        return obj.user.last_login

    def date_joined(self, obj):
        return obj.user.date_joined

    def get_actions(self, request):
        """Return bulk actions for UserAdmin without bulk delete."""
        actions = super(UserProfileAdmin, self).get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    def index_profiles(self, request):
        """Fire an Elastic Search Index Profiles task."""
        index_all_profiles()
        messages.success(request, 'Profile indexing started.')
        return HttpResponseRedirect(reverse('admin:users_userprofile_changelist'))

    def get_urls(self):
        """Return custom and UserProfileAdmin urls."""

        def wrap(view):

            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        urls = super(UserProfileAdmin, self).get_urls()
        my_urls = patterns('', url(r'index_profiles', wrap(self.index_profiles),
                                   name='users_index_profiles'))
        return my_urls + urls

admin.site.register(UserProfile, UserProfileAdmin)


class NullProfileFilter(SimpleListFilter):
    """Admin filter for null profiles."""
    title = 'has user profile'
    parameter_name = 'has_user_profile'

    def lookups(self, request, model_admin):
        return (('False', 'No'),
                ('True', 'Yes'))

    def queryset(self, request, queryset):
        if not self.value():
            return queryset
        value = self.value() != 'True'
        return queryset.filter(userprofile__isnull=value)


class UserAdmin(UserAdmin):
    list_filter = [NullProfileFilter]

admin.site.unregister(User)
admin.site.register(User, UserAdmin)


class GroupAdmin(ExportMixin, GroupAdmin):
    pass

admin.site.register(Group, GroupAdmin)


class VouchAdminForm(forms.ModelForm):

    class Meta:
        model = Vouch
        widgets = {
            'voucher': autocomplete_light.ChoiceWidget('UserProfiles'),
            'vouchee': autocomplete_light.ChoiceWidget('UserProfiles'),
        }


class VouchAdmin(admin.ModelAdmin):
    save_on_top = True
    search_fields = ['voucher__user__username', 'voucher__full_name',
                     'vouchee__user__username', 'vouchee__full_name']
    readonly_fields = ['date']
    list_display = ['vouchee', 'voucher', 'date', 'autovouch']
    list_filter = ['autovouch']
    form = VouchAdminForm

admin.site.register(Vouch, VouchAdmin)
