from django.contrib import admin

import autocomplete_light
from import_export.admin import ExportMixin

from models import APIApp, APIv2App


class APIAppAdmin(ExportMixin, admin.ModelAdmin):
    """APIApp Admin."""
    list_display = ['name', 'key', 'owner', 'is_mozilla_app', 'is_active']
    list_filter = ['is_mozilla_app', 'is_active']
    form = autocomplete_light.modelform_factory(APIApp)

admin.site.register(APIApp, APIAppAdmin)


class APIv2AppAdmin(ExportMixin, admin.ModelAdmin):
    list_display = ['name', 'owner', 'privacy_level', 'enabled', 'last_used']
    list_filter = ['privacy_level', 'enabled']
    search_fields = ['name', 'key', 'owner__user__username']
    readonly_fields = ['last_used', 'created']
    form = autocomplete_light.modelform_factory(APIv2App)

    fieldsets = (
        ('Status', {
            'fields': ('enabled',),
        }),
        (None, {
            'fields': ('name', 'description', 'url', 'owner', 'privacy_level'),
        }),
        ('Important dates', {
            'fields': ('created', 'last_used')
        }),
        ('Key', {
            'fields': ('key',),
            'classes': ('collapse',)
        }),
    )

admin.site.register(APIv2App, APIv2AppAdmin)
