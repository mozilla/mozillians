from django.contrib import admin

from mozillians.common.mixins import MozilliansAdminExportMixin
from models import FunFact


class FunFactAdmin(MozilliansAdminExportMixin, admin.ModelAdmin):
    readonly_fields = ['result', 'created', 'updated']
    list_display = ['name', 'created', 'updated', 'result', 'is_published']

    def is_published(self, obj):
        return obj.published
    is_published.boolean = True

    def result(self, obj):
        return obj.execute()

admin.site.register(FunFact, FunFactAdmin)
