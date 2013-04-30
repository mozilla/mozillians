from django.contrib import admin

from models import FunFact


class FunFactAdmin(admin.ModelAdmin):
    readonly_fields = ['result', 'created', 'updated']
    list_display = ['name', 'created', 'updated', 'result', 'is_published']

    def is_published(self, obj):
        return obj.published
    is_published.boolean = True

    def result(self, obj):
        return obj.execute()

admin.site.register(FunFact, FunFactAdmin)
