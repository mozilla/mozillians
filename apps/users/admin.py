from datetime import datetime, timedelta

from celery.task.sets import TaskSet
from functools import update_wrapper
from django.conf.urls.defaults import patterns, url
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, User
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from apps.common.admin import export_as_csv_action

from .cron import index_all_profiles
from .models import UserProfile, UsernameBlacklist

admin.site.unregister(User)
admin.site.unregister(Group)

import tasks


def _update_basket(action, request, queryset):
    """Generic basket (un)subscribe for queryset."""
    userprofiles = UserProfile.objects.filter(user__in=queryset)
    ts = [getattr(tasks, action).subtask(args=[profile.id])
          for profile in userprofiles]
    TaskSet(ts).apply_async()
    messages.success(request, 'Basket update started.')


def subscribe_to_basket_action():
    """Subscribe to Basket action."""

    def subscribe_to_basket(modeladmin, request, queryset):
        """Subscribe to Basket or update details of already subscribed."""
        _update_basket('update_basket_task', request, queryset)
    subscribe_to_basket.short_description = 'Subscribe to or Update Basket'
    return subscribe_to_basket


def unsubscribe_from_basket_action():
    """Unsubscribe from Basket action."""

    def unsubscribe_from_basket(modeladmin, request, queryset):
        """Unsubscribe from Basket."""
        _update_basket('remove_from_basket_task', request, queryset)
    unsubscribe_from_basket.short_description = 'Unsubscribe from Basket'
    return unsubscribe_from_basket


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
            return queryset.filter(date_joined__year=self.value())
        return queryset


class LastLoginFilter(SimpleListFilter):
    """Admin filter for last login."""
    title = 'last login'
    parameter_name = 'last_login'

    def lookups(self, request, model_admin):
        return (('<6', 'Less than 6 months'),
                ('>6', 'Between 6 and 12 months'),
                ('>12', 'More than a year'))

    def queryset(self, request, queryset):
        half_year = datetime.today() - timedelta(days=180)
        full_year = datetime.today() - timedelta(days=360)

        if self.value() == '<6':
            return queryset.filter(last_login__gte=half_year)
        elif self.value() == '>6':
            return queryset.filter(last_login__lt=half_year,
                                   last_login__gt=full_year)
        elif self.value() == '>12':
            return queryset.filter(last_login__lt=full_year)
        return queryset


class UserProfileInline(admin.StackedInline):
    """UserProfile Inline model for UserAdmin."""
    model = UserProfile
    raw_id_fields = ['vouched_by']


class UserAdmin(UserAdmin):
    """User Admin."""
    inlines = [UserProfileInline]
    search_fields = ['userprofile__full_name', 'email', 'username',
                     'userprofile__ircname']
    list_filter = ['userprofile__is_vouched', DateJoinedFilter,
                   LastLoginFilter]
    save_on_top = True
    list_display = ['full_name', 'email', 'username', 'country', 'is_vouched',
                    'vouched_by']
    list_display_links = ['full_name', 'email', 'username']
    actions = [export_as_csv_action(fields=('username', 'email'), header=True),
               subscribe_to_basket_action(), unsubscribe_from_basket_action()]

    def country(self, obj):
        return obj.userprofile.country

    def is_vouched(self, obj):
        return obj.userprofile.is_vouched

    def vouched_by(self, obj):
        return obj.userprofile.vouched_by

    def index_profiles(self, request):
        """Fire an Elastic Search Index Profiles task."""
        index_all_profiles()
        messages.success(request, 'Profile indexing started.')
        return HttpResponseRedirect(reverse('admin:auth_user_changelist'))

    def get_urls(self):
        """Return custom and UserAdmin urls."""

        def wrap(view):

            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        urls = super(UserAdmin, self).get_urls()
        my_urls = patterns('',
                           url(r'index_profiles', wrap(self.index_profiles),
                               name='users_index_profiles'))
        return my_urls + urls

    def full_name(self, obj):
        return obj.userprofile.full_name

admin.site.register(User, UserAdmin)


class UsernameBlacklistAdmin(admin.ModelAdmin):
    """UsernameBlacklist Admin."""
    save_on_top = True
    search_fields = ['value']
    list_filter = ['is_regex']
    list_display = ['value', 'is_regex']

admin.site.register(UsernameBlacklist, UsernameBlacklistAdmin)
