from django.contrib import admin

from models import APIApp


class APIAppAdmin(admin.ModelAdmin):
    """APIApp Admin."""
    list_display = ['name', 'key', 'owner', 'is_mozilla_app', 'is_active']
    list_filter = ['is_mozilla_app', 'is_active']

admin.site.register(APIApp, APIAppAdmin)
