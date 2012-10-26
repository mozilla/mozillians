from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from models import UserProfile, UsernameBlacklist

admin.site.unregister(User)


class UserProfileInline(admin.StackedInline):
    """UserProfile Inline model for UserAdmin."""
    model = UserProfile


class UserAdmin(UserAdmin):
    """User Admin."""
    inlines = [UserProfileInline]
    search_fields = ['first_name', 'last_name', 'email', 'username',
                     'userprofile__ircname']
    list_filter = ['userprofile__is_vouched']
    save_on_top = True
    list_display = ['first_name', 'last_name', 'email', 'username', 'country',
                    'is_vouched', 'vouched_by']
    list_display_links = ['first_name', 'last_name', 'email', 'username']

    def country(self, obj):
        return obj.userprofile.country

    def is_vouched(self, obj):
        return obj.userprofile.is_vouched

    def vouched_by(self, obj):
        return obj.userprofile.vouched_by

admin.site.register(User, UserAdmin)


class UsernameBlacklistAdmin(admin.ModelAdmin):
    """UsernameBlacklist Admin."""
    save_on_top = True
    search_fields = ['value']
    list_filter = ['is_regex']
    list_display = ['value', 'is_regex']

admin.site.register(UsernameBlacklist, UsernameBlacklistAdmin)
