from django.conf import settings

import requests

from mozillians.geo.models import Country, Region, City

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


def reverse_geocode(lat, lng):
    """
    Given a lat and lng (floats), return a 3-tuple of
    Country, Region, and City objects.

    Raises exception if there's any error calling mapbox.
    """
    result = get_first_mapbox_geocode_result("%s,%s" % (lng, lat))
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


def result_to_country(result):
    """
    Given one result from mapbox, converted to a dictionary keyed on 'type',
    return a Country object or None
    """
    if 'country' in result:
        mapbox_country = result['country']
        country, created = Country.objects.get_or_create(
            mapbox_id=mapbox_country['id'],
            defaults=dict(
                name=mapbox_country['name'],
            )
        )
        if not created:
            # Update name if it's changed in mapbox
            if country.name != mapbox_country['name']:
                country.name = mapbox_country['name']
                country.save()
        return country


def result_to_region(result, country):
    """
    Given one result from mapbox and a Country object,
    return a Region object or None.
    """
    if 'province' in result:
        mapbox_region = result['province']
        region, created = Region.objects.get_or_create(
            mapbox_id=mapbox_region['id'],
            defaults=dict(
                name=mapbox_region['name'],
                country=country,
            )
        )
        if not created:
            # Update name if it's changed in mapbox
            if region.name != mapbox_region['name']:
                region.name = mapbox_region['name']
                region.save()
        return region


def result_to_city(result, country, region):
    """
    Given one result from mapbox, a Country, and an
    optional Region (or None), return a City object or None.
    """
    # City has more data, but is similar to region and country
    if 'city' in result:
        mapbox_city = result['city']
        defaults = dict(
                name=mapbox_city['name'],
                country=country,
                region=region,
                lat=mapbox_city['lat'],
                lng=mapbox_city['lon'],
            )
        city, created = City.objects.get_or_create(
            mapbox_id=mapbox_city['id'],
            defaults=defaults
        )
        if not created:
            # Update if anything has changed
            do_save = False
            for key, val in defaults.iteritems():
                if getattr(city, key) != val:
                    setattr(city, key, val)
                    do_save = True
            if do_save:
                city.save()
        return city
