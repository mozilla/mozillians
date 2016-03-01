from django.contrib import admin

from mozillians.geo.models import City, Country, Region


class CountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'code')
    readonly_fields = ('name', 'mapbox_id')
    seach_fields = ('name', 'code')

admin.site.register(Country, CountryAdmin)


class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'country')
    readonly_fields = ('name', 'country', 'mapbox_id')
    search_fields = ('name', 'country__name', 'country__code')

admin.site.register(Region, RegionAdmin)


class CityAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'country', 'lng', 'lat')
    readonly_fields = ('country', 'region', 'name', 'lat', 'lng', 'mapbox_id')
    search_fields = ('name', 'region__name', 'country__name', 'country__code')

admin.site.register(City, CityAdmin)
