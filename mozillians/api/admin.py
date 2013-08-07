from django.contrib import admin

import autocomplete_light

from models import APIApp


class APIAppAdmin(admin.ModelAdmin):
    """APIApp Admin."""
    list_display = ['name', 'key', 'owner', 'is_mozilla_app', 'is_active']
    list_filter = ['is_mozilla_app', 'is_active']
    form = autocomplete_light.modelform_factory(APIApp)

admin.site.register(APIApp, APIAppAdmin)
