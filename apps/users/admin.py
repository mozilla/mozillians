from django.contrib import admin

from sorl.thumbnail.admin import AdminImageMixin

from users.models import UserProfile, UsernameBlacklist


class UserProfileAdmin(AdminImageMixin, admin.ModelAdmin):
    fields = ['user', 'user_email', 'display_name', 'photo', 'ircname',
              'is_vouched', 'vouched_by', 'bio', 'website', 'groups', 'skills',
              'languages', 'country', 'region', 'city']
    list_display = ['display_name', 'user_email', 'user_username', 'country',
                    'is_vouched', 'vouched_by']
    list_display_links = ['display_name', 'user_email', 'user_username']
    readonly_fields = ['user', 'user_email']
    save_on_top = True
    search_fields = ['display_name', 'user__email', 'user__username',
                     'ircname']
    list_filter = ['is_vouched']

    def has_add_permission(self, *a, **kw):
        """No one should be creating UserProfiles from the admin."""
        return False

    def has_delete_permission(self, *a, **kw):
        """Delete the User, not the UserProfile."""
        return False

admin.site.register(UserProfile, UserProfileAdmin)


class UsernameBlacklistAdmin(admin.ModelAdmin):
    save_on_top = True
    search_fields = ['value']
    list_filter = ['is_regex']
    list_display = ['value', 'is_regex']

admin.site.register(UsernameBlacklist, UsernameBlacklistAdmin)
