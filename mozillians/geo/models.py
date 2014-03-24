from django.db import models

from mozillians.users.models import COUNTRIES, UserProfile

from tower import ugettext_lazy as _lazy


class Country(models.Model):
    #  {u'type': u'country', u'id': u'country.4150104525', u'name': u'United States'}
    name = models.CharField(
        max_length=120, unique=True,
        help_text='name field from Mapbox'
    )
    code = models.CharField(
        max_length=2,
        help_text='lowercased 2-letter code from Mozilla product data')
    mapbox_id = models.CharField(
        max_length=40, unique=True,
        help_text="'id' field from Mapbox"
    )

    class Meta(object):
        verbose_name_plural = 'Countries'

    def __unicode__(self):
        return self.name


class Region(models.Model):
    # {u'type': u'province', u'id': u'province.2516948401', u'name': u'North Carolina'}
    name = models.CharField(
        max_length=120,
        help_text='name field from Mapbox'
    )
    mapbox_id = models.CharField(
        max_length=40, unique=True,
        help_text="'id' field from Mapbox"
    )
    country = models.ForeignKey(Country)

    class Meta(object):
        unique_together = (
            ('name', 'country'),
        )

    def __unicode__(self):
        return u'%s, %s' % (self.name, self.country.name)


class City(models.Model):
    # {u'name': u'Carrboro', u'lon': -79.083798999999999, u'lat': 35.918596000000001,
    # u'bounds': [-79.100728852067547, 35.889960723848048,
    #             -79.063862048216336, 35.947221266002018],
    # u'type': u'city', u'id': u'mapbox-places.27510'}
    name = models.CharField(
        max_length=120,
        help_text='name field from Mapbox'
    )
    mapbox_id = models.CharField(
        max_length=40, unique=True,
        help_text="'id' field from Mapbox"
    )
    region = models.ForeignKey(Region, null=True, blank=True)
    country = models.ForeignKey(Country)
    lat = models.FloatField()
    lng = models.FloatField()

    class Meta:
        verbose_name_plural = 'Cities'
        unique_together = (
            ('name', 'region', 'country'),
        )

    def __unicode__(self):
        return u', '.join([x.name for x in self, self.region, self.country if x])


class Geocoding(models.Model):
    """
    This is a record of how we geocoded particular inputs, so we don't need to hit
    mapbox again, and we can dump this data from a developer system and then use
    it against another database.

    To dump the geo data easily:

    $ python manage.py dumpdata --natural --indent=2 geo >geo.json
    """
    # Inputs
    country = models.CharField(max_length=50, default='',
                               choices=COUNTRIES.items(),
                               verbose_name=_lazy(u'Country'))
    region = models.CharField(max_length=255, default='', blank=True,
                              verbose_name=_lazy(u'Province/State'))
    city = models.CharField(max_length=255, default='', blank=True,
                            verbose_name=_lazy(u'City'))

    # Outputs
    geo_country = models.ForeignKey('geo.Country')
    geo_region = models.ForeignKey('geo.Region', null=True, blank=True, on_delete=models.SET_NULL)
    geo_city = models.ForeignKey('geo.City', null=True, blank=True, on_delete=models.SET_NULL)

    #
    def apply(self):
        """
        Apply data from this record to userprofiles
        :return: count of updated records
        """
        count = UserProfile.objects.filter(
            city__iexact=self.city,
            region__iexact=self.region,
            country__iexact=self.country,
            geo_country=None,  # not already geocoded
        ).update(
            geo_country=self.geo_country,
            geo_region=self.geo_region,
            geo_city=self.geo_city,
        )
        # If we have a lat/lng for the city, and any of these users
        # don't, copy it to their user profile as their lat/lng.
        if self.geo_city and self.geo_city.lat is not None and self.geo_city.lng is not None:
            UserProfile.objects.filter(
                city__iexact=self.city,
                region__iexact=self.region,
                country__iexact=self.country,
                lat=None,
                lng=None,
            ).update(
                lat=self.geo_city.lat,
                lng=self.geo_city.lng,
            )
        return count

    @classmethod
    def remember(cls, profile):
        """
        Given a geocoded profile, get or create a Geocoding record
        with the geocoded data from it.

        :param profile:
        :return: the Geocoding record
        """
        geocoding, created = Geocoding.objects.get_or_create(
            city=profile.city,
            region=profile.region,
            country=profile.country,
            defaults=dict(
                geo_city=profile.geo_city,
                geo_region=profile.geo_region,
                geo_country=profile.geo_country,
                )
        )
        return geocoding
