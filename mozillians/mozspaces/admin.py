from django import forms
from django.contrib import admin
from django.core.urlresolvers import reverse
from product_details import product_details
from sorl.thumbnail.admin import AdminImageMixin

import autocomplete_light

from models import Keyword, MozSpace, Photo


class KeywordAdmin(admin.StackedInline):
    """ Keyword Inline Admin."""
    model = Keyword


class PhotoAdmin(AdminImageMixin, admin.StackedInline):
    """ Photo Inline Admin."""
    model = Photo


class MozSpaceAdminForm(forms.ModelForm):
    """MozSpace Admin Form."""

    def __init__(self, *args, **kwargs):
        super(MozSpaceAdminForm, self).__init__(*args, **kwargs)
        queryset = Photo.objects.none()
        if 'instance' in kwargs:
            queryset = Photo.objects.filter(mozspace__id=kwargs['instance'].id)
        self.fields['cover_photo'].queryset = queryset

    class meta:
        model = MozSpace


class MozSpaceAdmin(admin.ModelAdmin):
    form = MozSpaceAdminForm
    inlines = [PhotoAdmin, KeywordAdmin]
    search_fields = ['name']
    list_display = ['name', 'city', 'country', 'coordinator_link']
    form = autocomplete_light.modelform_factory(MozSpace)

    def coordinator_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.id])
        full_name = obj.coordinator.userprofile.full_name
        return u'<a href="%s">%s</a>' % (url, full_name)
    coordinator_link.allow_tags = True
    coordinator_link.short_description = 'coordinator'

    def country(self, obj):
        return product_details.get_regions('en-US')[obj.country]


admin.site.register(MozSpace, MozSpaceAdmin)
