from django.contrib import admin

from sorl.thumbnail.admin import AdminImageMixin

from users.models import UserProfile

class UserProfileAdmin(AdminImageMixin, admin.ModelAdmin):
    pass

admin.site.register(UserProfile, UserProfileAdmin)
