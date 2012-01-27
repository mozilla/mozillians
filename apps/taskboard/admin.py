from django.contrib import admin

from taskboard.models import Task


def mark_disabled(modeladmin, request, queryset):
    queryset.update(disabled=True)
mark_disabled.short_description = "Disable selected tasks"


def mark_enabled(modeladmin, request, queryset):
    queryset.update(disabled=False)
mark_enabled.short_description = "Enable selected tasks"


class TaskAdmin(admin.ModelAdmin):
    actions = (mark_disabled, mark_enabled)
    list_display = ('summary', 'contact', 'deadline', 'created', 'disabled')
    list_filter = ('deadline', 'created', 'disabled')
    ordering = ('-created',)
    search_fields = ('summary', 'contact__username', 'instructions')
    readonly_fields = ('created',)


admin.site.register(Task, TaskAdmin)
