from django.contrib import admin

from sorl.thumbnail.admin import AdminImageMixin

from users.models import UserProfile


class UserProfileAdmin(AdminImageMixin, admin.ModelAdmin):
    list_display = ['display_name', 'user_email', 'user_username', 'ircname',
                    'is_vouched', 'vouched_by']
    list_display_links = ['display_name', 'user_email', 'user_username']
    search_fields = ['display_name', 'user_email', 'user_username', 'ircname']

admin.site.register(UserProfile, UserProfileAdmin)
