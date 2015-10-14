import logging
import requests
from requests import ConnectionError, HTTPError

from django.conf import settings
from django.db.models import Q

from product_details import product_details

from mozillians.geo.models import Country, Region, City


logger = logging.getLogger(__name__)

# Example data from mapbox:
# {
#     u'query': [-79.083798999999999, 35.918596000000001],
#     u'attribution': {
#         u'mapbox-places':
#             u"<a href='https://www.mapbox.com/about/maps/' target='_blank'>&copy; Mapbox "
#             u"&copy; OpenStreetMap</a> <a class='mapbox-improve-map' "
#             u"href='https://www.mapbox.com/map-feedback/' "
#             u"target='_blank'>Improve this map</a>"
#     },
#     u'results': [
#         [
#             {u'lat': 35.917845900000003, u'type': u'street', u'lon': -79.083291000000003,
#              u'id': u'street.16712017', u'name': u'Hillsborough Rd'},
#             {u'name': u'Carrboro', u'lon': -79.083798999999999,
#              u'bounds': [-79.100728852067547, 35.889960723848048, -79.063862048216336,
#                          35.947221266002018],
#              u'lat': 35.918596000000001, u'type': u'city', u'id': u'mapbox-places.27510'},
#             {u'name': u'North Carolina', u'lon': -78.717434999999995,
#              u'bounds': [-84.321869000000007, 33.752877999999981, -75.400119000000004,
#                          36.588156999999995],
#              u'lat': 35.182879999999997, u'type': u'province', u'id': u'province.2516948401'},
#             {u'name': u'United States', u'lon': -99.041505000000001,
#              u'bounds': [-179.23108600000003, 18.865459999999985, 179.85968099999997,
#                          71.441058999999996], u'lat': 37.940711,
#              u'type': u'country', u'id': u'country.4150104525'}
#         ]
#     ]
# }


class GeoLookupException(Exception):
    pass


def reverse_geocode(lat, lng):
    """
    Given a lat and lng (floats), return a 3-tuple of
    Country, Region, and City objects.

    Raises exception if there's any error calling mapbox.
    """
    try:
        result = get_first_mapbox_geocode_result('%s,%s' % (lng, lat))
    except HTTPError:
        logger.exception('HTTP status error when calling Mapbox.')
        raise GeoLookupException
    except ConnectionError:
        logger.exception('Cannot open connection to Mapbox.')
        raise GeoLookupException

    if result:
        return result_to_country_region_city(result)
    else:
        return None, None, None


def get_first_mapbox_geocode_result(query):
    """
    Pass `query` string as the query to mapbox reverse geocoding API.
    Returns the first result, converted to a dictionary keyed on type
    (e.g. 'city', 'province', 'country', etc.)

    If an error happens, requests raises HTTPError.

    If no results are returned, returns an empty dictionary.
    """
    map_id = settings.MAPBOX_MAP_ID
    url = 'http://api.tiles.mapbox.com/v3/%s/geocode/%s.json' % (map_id, query)

    r = requests.get(url)
    r.raise_for_status()
    data = r.json()

    # Convert first result to a dictionary indexed by result type
    if data.get('results'):
        result = data['results'][0]
        result = dict([(item['type'], item) for item in result])
        return result
    return {}


def result_to_country_region_city(result):
    """
    Given one result from mapbox, converted to a dictionary keyed on 'type',
    return a 3-tuple of Country, Region, City objects.
    (Any of them MIGHT be None).
    """
    country = result_to_country(result)
    if country:
        region = result_to_region(result, country)
        city = result_to_city(result, country, region)
    else:
        region = city = None
    return country, region, city


def deduplicate_countries(country, dup_country):
    """
    Given 2 Country instances, deduplicate dup_country and it's references.
    """
    # Deduplicate geo data
    regions = dup_country.region_set.all()
    if regions.exists():
        regions.update(country=country)

    cities = dup_country.city_set.all()
    if cities.exists():
        cities.update(country=country)

    # Deduplicate user data
    users = dup_country.userprofile_set.all()
    if users.exists():
        users.update(geo_country=country)

    dup_country.delete()


def result_to_country(result):
    """
    Given one result from mapbox, converted to a dictionary keyed on 'type',
    return a Country object or None
    """
    if 'country' in result:

        mapbox_country = result['country']
        codes = dict((v, k) for k, v in product_details.get_regions('en-US').iteritems())
        code = codes.get(mapbox_country['name'], '')
        lookup_args = {
            'name': mapbox_country['name']
        }
        args = {
            'mapbox_id': mapbox_country['id'],
            'code': code
        }

        args.update(lookup_args)

        query = Q(**lookup_args) | Q(mapbox_id=mapbox_country['id'])
        country_qs = Country.objects.filter(query).distinct()

        if country_qs.exists():
            # Check if deduplication is required
            if country_qs.count() == 2:
                deduplicate_countries(country_qs[0], country_qs[1])

            country_qs.update(**args)
            country = country_qs[0]
        else:
            country = Country.objects.create(**args)

        return country


def deduplicate_regions(region, dup_region):
    """
    Given 2 Country instances, deduplicate dup_country and it's references.
    """
    # Deduplicate geo data
    cities = dup_region.city_set.all()
    if cities.exists():
        cities.update(region=region)

    # Deduplicate user data
    users = dup_region.userprofile_set.all()
    if users.exists():
        users.update(geo_region=region)

    dup_region.delete()


def result_to_region(result, country):
    """
    Given one result from mapbox and a Country object,
    return a Region object or None.
    """
    if 'province' in result:
        mapbox_region = result['province']
        lookup_args = {
            'name': mapbox_region['name'],
            'country': country
        }

        args = {
            'mapbox_id': mapbox_region['id']
        }

        args.update(lookup_args)

        query = Q(**lookup_args) | Q(mapbox_id=mapbox_region['id'])
        region_qs = Region.objects.filter(query).distinct()

        if region_qs.exists():
            if region_qs.count() == 2:
                deduplicate_regions(region_qs[0], region_qs[1])
            region_qs.update(**args)
            region = region_qs[0]
        else:
            region = Region.objects.create(**args)

        return region


def deduplicate_cities(city, dup_city):
    """
    Given 2 City instances, deduplicate dup_city and it's references to city.
    """
    users = dup_city.userprofile_set.all()
    if users.exists():
        users.update(geo_city=city, geo_region=city.region, geo_country=city.country)
    dup_city.delete()


def result_to_city(result, country, region):
    """
    Given one result from mapbox, a Country, and an
    optional Region (or None), return a City object or None.
    """
    # City has more data, but is similar to region and country
    if 'city' in result:
        mapbox_city = result['city']
        lookup_args = {
            'name': mapbox_city['name'],
            'country': country,
            'region': region,
        }
        args = {
            'mapbox_id': mapbox_city['id'],
            'lat': mapbox_city['lat'],
            'lng': mapbox_city['lon'],
        }

        args.update(lookup_args)

        # Mapbox sometimes returns multiple cities with the same
        # name but different ids. On top of that there is a possibility
        # to return updated data for a specific mapbox_id that might collide
        # with an existing DB entry, thus raising an IntegrityError for key
        # (name, region, country). In that case we need to deduplicate City
        # instances and its references.

        query = Q(**lookup_args) | Q(mapbox_id=mapbox_city['id'])
        city_qs = City.objects.filter(query).distinct()

        if city_qs.exists():
            # Check if deduplication is required
            if city_qs.count() == 2:
                deduplicate_cities(city_qs[0], city_qs[1])

            # Update DB with new geocoding data for city instance
            city_qs.update(**args)
            city = city_qs[0]

        else:
            city = City.objects.create(**args)

        return city
