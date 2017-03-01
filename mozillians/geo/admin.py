from django.contrib import admin

from mozillians.common.mixins import MozilliansAdminExportMixin
from mozillians.geo.models import City, Country, Region


class CountryAdmin(MozilliansAdminExportMixin, admin.ModelAdmin):
    list_display = ('name', 'code')
    readonly_fields = ('name',)
    search_fields = ('name', 'code')


admin.site.register(Country, CountryAdmin)


class RegionAdmin(MozilliansAdminExportMixin, admin.ModelAdmin):
    list_display = ('name', 'country')
    readonly_fields = ('name', 'country',)
    search_fields = ('name', 'country__name', 'country__code')


admin.site.register(Region, RegionAdmin)


class CityAdmin(MozilliansAdminExportMixin, admin.ModelAdmin):
    list_display = ('name', 'region', 'country', 'lng', 'lat')
    readonly_fields = ('country', 'region', 'name', 'lat', 'lng',)
    search_fields = ('name', 'region__name', 'country__name', 'country__code')


admin.site.register(City, CityAdmin)
