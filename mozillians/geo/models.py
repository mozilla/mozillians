from django.db import models


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
