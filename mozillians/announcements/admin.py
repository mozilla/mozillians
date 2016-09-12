from django.contrib import admin

from sorl.thumbnail.admin import AdminImageMixin

from mozillians.common.mixins import MozilliansAdminExportMixin
from models import Announcement


class AnnouncementAdmin(AdminImageMixin, MozilliansAdminExportMixin, admin.ModelAdmin):
    save_on_top = True
    readonly_fields = ['created', 'updated', 'is_published']
    search_fields = ['title']
    list_display = ['title', 'publish_from', 'publish_until', 'is_published']
    list_editable = ['publish_from', 'publish_until']

    def is_published(self, obj):
        return obj.published
    is_published.boolean = True

admin.site.register(Announcement, AnnouncementAdmin)
