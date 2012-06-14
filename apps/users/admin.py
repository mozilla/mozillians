from django.contrib import admin

from sorl.thumbnail.admin import AdminImageMixin

from users.models import UserProfile


class UserProfileAdmin(AdminImageMixin, admin.ModelAdmin):
    fields = ['user', 'user_email', 'display_name', 'photo', 'ircname',
              'is_vouched', 'vouched_by', 'bio', 'website', 'groups', 'skills']
    list_display = ['display_name', 'user_email', 'user_username', 'ircname',
                    'is_vouched', 'vouched_by']
    list_display_links = ['display_name', 'user_email', 'user_username']
    readonly_fields = ['user', 'user_email']
    save_on_top = True
    search_fields = ['display_name', 'user__email', 'user__username',
                     'ircname']

    def has_add_permission(self, *a, **kw):
        """No one should be creating UserProfiles from the admin."""
        return False

    def has_delete_permission(self, *a, **kw):
        """Delete the User, not the UserProfile."""
        return False

admin.site.register(UserProfile, UserProfileAdmin)
