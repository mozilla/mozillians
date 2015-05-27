from django.contrib import admin

import autocomplete_light
from import_export import fields
from import_export.admin import ExportMixin
from import_export.resources import ModelResource

from models import APIApp, APIv2App


class APIAppResource(ModelResource):
    """APIApp admin export resource."""
    email = fields.Field(attribute='owner__email')

    class Meta:
        model = APIApp


class APIAppAdmin(ExportMixin, admin.ModelAdmin):
    """APIApp Admin."""

    list_display = ['name', 'key', 'owner', 'owner_email', 'is_mozilla_app', 'is_active']
    list_filter = ['is_mozilla_app', 'is_active']

    def owner_email(self, obj):
        return obj.owner.email

    owner_email.admin_order_field = 'owner__email'
    owner_email.short_description = 'Email'

    form = autocomplete_light.modelform_factory(APIApp)
    resource_class = APIAppResource

admin.site.register(APIApp, APIAppAdmin)


class APIv2AppResource(ModelResource):
    """APIApp admin export resource."""
    email = fields.Field(attribute='owner__email')

    class Meta:
        model = APIv2App


class APIv2AppAdmin(ExportMixin, admin.ModelAdmin):
    """APIv2App Admin."""
    list_display = ['name', 'owner', 'owner_email', 'privacy_level', 'enabled', 'last_used']
    list_filter = ['privacy_level', 'enabled']
    search_fields = ['name', 'key', 'owner__user__username']
    readonly_fields = ['last_used', 'created']

    def owner_email(self, obj):
        return obj.owner.user.email

    owner_email.admin_order_field = 'owner__user__email'
    owner_email.short_description = 'Email'

    form = autocomplete_light.modelform_factory(APIv2App)
    resource_class = APIv2AppResource

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
