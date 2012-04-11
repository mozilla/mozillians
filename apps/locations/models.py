from django.contrib.gis.db import models

from product_details import product_details
from tower import ugettext_lazy as _lazy

from locations.tasks import geocode_address


# Country keys are the same in all languages, so it doesn't matter which
# locale we use.
COUNTRIES = product_details.get_regions('en-US')


class Country(models.Model):
    """The largest container for a location (state, city, etc.).

    Our list of countries is populated and localized by the ``product_details``
    library. It is *not* a user-generated list and should not be modified by
    hand; let ``product_details`` take care of everything.

    If it turns out we're missing a country, we should address it upstream.
    """
    @classmethod
    def localized_list(cls, locale='en-US'):
        """A list of all countries in the DB, with their names localized."""
        regions = product_details.get_regions(locale)
        countries = [(c.id, regions[c.code]) for c in cls.objects.all()]
        return sorted(countries, key=lambda country: country[1])

    code = models.CharField(max_length=255, unique=True,
                            choices=COUNTRIES.items())

    #: We don't use SPATIAL indexes because we're using MySQL InnoDB tables.
    #: TODO: Add indexes when we go PostgreSQL by removing the
    #:       ``spatial_index=False`` argument.
    poly = models.PolygonField(null=True, spatial_index=False)

    def name(self, locale='en-US'):
        """Return the name of this country in the locale specified.

        Defaults to en-US if no locale is specified.
        """
        return product_details.get_regions(locale)[self.code]

    def __unicode__(self):
        """Return the name of this country in English."""
        return self.name()


class Address(models.Model):
    """An address is a user's full street address including country."""
    #: An address belongs to a User. They're created when a User is created.
    street = models.CharField(max_length=200, verbose_name=_lazy(u'Address'), blank=True, null=True)
    city = models.CharField(max_length=150, verbose_name=_lazy(u'City'), blank=True, null=True)  # Bangkok, lol.
    province = models.CharField(max_length=200, verbose_name=_lazy(u'Province/State'), blank=True, null=True)
    postal_code = models.CharField(max_length=50, verbose_name=_lazy(u'Postal/Zip Code'), blank=True, null=True)
    country = models.ForeignKey('Country', null=True)

    #: We don't use SPATIAL indexes because we're using MySQL InnoDB tables.
    #: TODO: Add indexes when we go PostgreSQL.
    point = models.PointField(null=True, spatial_index=False)

    objects = models.GeoManager()

    def save(self, *args, **kwargs):
        """
        Defaults to updating the point on the model. If update_point=False
        is passed in, then don't trigger the celery task.
        """
        update_point = kwargs.get('update_point', True)
        if 'update_point' in kwargs:
            del(kwargs['update_point'])

        super(Address, self).save(*args, **kwargs)

        if update_point:
            geocode_address.apply_async(args=[self.id])

    def formatted(self, *args, **kwargs):
        """Return this address with only the specified attributes."""
        if not args:
            args = ['city', 'province', 'country']
        locale = kwargs.get('locale')

        address = ', '.join([unicode(getattr(self, a)) for a in args
                if a is not 'country' and getattr(self, a)])

        if self.country and locale:
            return '%s, %s' % (address, self.country.name(locale))
        elif self.country:
            return '%s, %s' % (address, self.country.name())
        else:
            return address

    def __unicode__(self):
        """Return the fully formatted contents of this address."""
        return self.formatted('street', 'city', 'province', 'postal_code',
                              'country')
