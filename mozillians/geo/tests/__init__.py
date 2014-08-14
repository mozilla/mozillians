import random

import factory

from mozillians.geo.models import City, Country, Region


class CountryFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Country
    name = factory.Sequence(lambda n: 'Country Name {0}'.format(n))
    mapbox_id = factory.Sequence(lambda n: 'country.{0}'.format(n))
    # Not really unique, but we need to convert sequences to a max
    # of two characters somehow.
    code = factory.Sequence(lambda n: '{0}'.format(str(n)[-2:]))


class RegionFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Region
    name = factory.Sequence(lambda n: 'Region Name {0}'.format(n))
    mapbox_id = factory.Sequence(lambda n: 'province.{0}'.format(n))
    country = factory.SubFactory(CountryFactory)


class CityFactory(factory.DjangoModelFactory):
    FACTORY_FOR = City
    name = factory.Sequence(lambda n: 'City Name {0}'.format(n))
    mapbox_id = factory.Sequence(lambda n: 'city.{0}'.format(n))
    lat = factory.LazyAttribute(lambda o: random.uniform(-90.0, 90.0))
    lng = factory.LazyAttribute(lambda o: random.uniform(-180.0, 180.0))
    region = factory.SubFactory(RegionFactory)
    country = factory.SelfAttribute('region.country')
