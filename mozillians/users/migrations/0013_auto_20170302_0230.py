# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.db.models import Q


def migrate_countries(apps, schema_editor):
    UserProfile = apps.get_model('users', 'UserProfile')

    # cities_light data models
    Country = apps.get_model('cities_light', 'Country')

    for profile in UserProfile.objects.filter(geo_country__isnull=False):

        # Query countries based on `name` and `alternate_names`
        country_query = (Q(name=profile.geo_country.name) |
                         Q(alternate_names__icontains=profile.geo_country.name))
        cities_countries = Country.objects.filter(country_query)

        country = None
        if cities_countries.exists():
            country = cities_countries[0]

        kwargs = {
            'country': country,
            'privacy_country': profile.privacy_geo_country
        }
        UserProfile.objects.filter(pk=profile.id).update(**kwargs)


def migrate_cities_regions(apps, schema_editor):
    UserProfile = apps.get_model('users', 'UserProfile')
    City = apps.get_model('cities_light', 'City')

    for profile in UserProfile.objects.filter(country__isnull=False, geo_city__isnull=False):

        # Query cities based on `name`, `alternate_names` and `country`
        city_query = ((Q(name=profile.geo_city.name) |
                       Q(alternate_names__icontains=profile.geo_city.name)) &
                      Q(country=profile.country))

        city = None
        region = None
        cities = City.objects.filter(city_query)
        if cities.exists():
            city = cities[0]
            region = city.region

        kwargs = {
            'region': region,
            'city': city,
            'privacy_region': profile.privacy_geo_region,
            'privacy_city': profile.privacy_geo_city
        }

        UserProfile.objects.filter(pk=profile.id).update(**kwargs)


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_auto_20170220_0715'),
    ]

    operations = [
        migrations.RunPython(migrate_countries, backwards),
        migrations.RunPython(migrate_cities_regions, backwards),
    ]
