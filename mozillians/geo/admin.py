from django.contrib import admin

from mozillians.geo.models import City, Country, Geocoding, Region


admin.site.register(
    Geocoding,
    list_display=('country', 'region', 'city', 'geo_country', 'geo_region', 'geo_city'),
)

admin.site.register(
    Country,
    list_display=('name', 'code'),
    readonly_fields=('name', 'code', 'mapbox_id'),
    seach_fields=('name', 'code'),
)

admin.site.register(
    Region,
    list_display=('name', 'country'),
    readonly_fields=('name', 'country', 'mapbox_id'),
    search_fields=('name', 'country__name', 'country__code'),
)

admin.site.register(
    City,
    list_display=('name', 'region', 'country', 'lng', 'lat'),
    readonly_fields=('country', 'region', 'name', 'lat', 'lng', 'mapbox_id'),
    search_fields=('name', 'region__name', 'country__name', 'country__code'),
)
