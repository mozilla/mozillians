from django.contrib import admin

from mozillians.phonebook.models import Invite


class InviteAdmin(admin.ModelAdmin):
    search_fields = ['recipient', 'inviter', 'code']
    list_display = ['recipient', 'inviter', 'code', 'redeemer']


admin.site.register(Invite, InviteAdmin)
