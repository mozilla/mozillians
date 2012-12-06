from functools import update_wrapper
from django.conf.urls.defaults import patterns, url
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group, User
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect

from .cron import index_all_profiles
from .models import UserProfile, UsernameBlacklist

admin.site.unregister(User)
admin.site.unregister(Group)


class UserProfileInline(admin.StackedInline):
    """UserProfile Inline model for UserAdmin."""
    model = UserProfile
    raw_id_fields = ['vouched_by']


class UserAdmin(UserAdmin):
    """User Admin."""
    inlines = [UserProfileInline]
    search_fields = ['userprofile__full_name', 'email', 'username',
                     'userprofile__ircname']
    list_filter = ['userprofile__is_vouched']
    save_on_top = True
    list_display = ['full_name', 'email', 'username', 'country', 'is_vouched',
                    'vouched_by']
    list_display_links = ['full_name', 'email', 'username']

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
