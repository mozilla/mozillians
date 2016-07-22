from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from mozillians.common.mixins import MozilliansAdminExportMixin
from mozillians.phonebook.models import Invite


class RedeemedInviteFilter(SimpleListFilter):
    title = 'Redeemed'
    parameter_name = 'redeemed'

    def lookups(self, request, model_admin):
        return (('False', 'No'),
                ('True', 'Yes'))

    def queryset(self, request, queryset):
        if self.value() is None:
            return queryset

        if self.value() == 'True':
            return queryset.filter(redeemer__isnull=False)

        return queryset.filter(redeemer__isnull=True)


class InviteAdmin(MozilliansAdminExportMixin, admin.ModelAdmin):
    search_fields = ['recipient', 'inviter', 'code']
    list_display = ['recipient', 'inviter', 'code', 'redeemer']
    readonly_fields = ['inviter', 'recipient', 'redeemer', 'code', 'redeemed', 'created']
    list_filter = [RedeemedInviteFilter]


admin.site.register(Invite, InviteAdmin)
