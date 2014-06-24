from collections import defaultdict
import urllib
from mozillians.geo.models import Country, Region, City, Geocoding
import requests

from product_details import product_details


from django.core.management.base import BaseCommand
from mozillians.users.models import UserProfile
from mozillians.settings import MAPBOX_MAP_ID

COUNTRIES = product_details.get_regions('en-US')


def country_code_to_mapbox_name(code):
    try:
        country = Country.objects.get(code=code)
    except Country.DoesNotExist:
        country_name = COUNTRIES[code.lower()]
        # Change country name to match mapbox
        # This is not a political statement, it's merely
        # using the same name as Mapbox has already chosen.
        if country_name == 'Guinea-Bissau':
            country_name = 'Guinea Bissau'
        elif country_name == 'Hong Kong':
            country_name = 'Hong Kong S.A.R.'
        elif country_name == 'Macedonia, F.Y.R. of':
            country_name = 'Macedonia'
        elif country_name == 'Russian Federation':
            country_name = 'Russia'
        elif country_name == 'Occupied Palestinian Territory':
            country_name = 'Palestine'
        return country_name
    else:
        return country.name


def massage_results(country_code, results):
    """
    Given a list of results returned by mapbox.

    Return a dictionary that might have entries 'city', 'region',
    and/or 'country'. Only include an entry if the results contained
    exactly one instance of that type.

    E.g. if we got back five results, but the only country in any
    of them was Albania, then the dictionary returned will have a 'country'
    entry with the data for Albania.

    The idea is that sometimes the results from Mapbox don't look unique,
    but enough of the results are unique to be useful to us.

    Each entry we return is an instance of the appropriate model.

    :param results:
    :return:
    """
    print(results)

    country_code = country_code.lower()

    try:
        country = Country.objects.get(code=country_code)
    except Country.DoesNotExist:
        country_name = country_code_to_mapbox_name(country_code)
        country = None
    else:
        country_name = country.name

    countries = {}
    regions = {}
    cities = {}

    sets = defaultdict(set)
    for result in results:
        # Convert list of dictionaries to a dictionary keyed by the type
        result = dict([(item['type'], item) for item in result])

        if 'country' not in result:
            print('SKIPPING result - no country')
            continue

        # Ignore any result that isn't in this user's country
        # FIXME: This breaks if our country names don't match Mapbox's, and they probably
        # don't all match.
        result_name = result['country']['name']
        if result_name != country_name:
            print('SKIPPING result - wrong country - %s != %s' % (result['country']['name'],
                                                                  country_name))
            continue

        if 'city' in result:
            name = result['city']['name']
            cities[name] = result['city']
            sets['city'].add(name)
        if 'province' in result:
            name = result['province']['name']
            regions[name] = result['province']
            sets['region'].add(name)
        if 'country' in result:
            name = result['country']['name']
            countries[name] = result['country']
            sets['country'].add(name)
    retval = {}

    city = region = None
    if not country and len(sets['country']) == 1:
        name = list(sets['country'])[0]
        item = countries[name]
        country, unused = Country.objects.get_or_create(
            mapbox_id=item['id'],
            defaults=dict(
                name=item['name'],
                code=country_code,
                mapbox_id=item['id'],
            )
        )
    if country:
        retval['country'] = country

    # Can't do anything with a region without a country
    if country and len(sets['region']) == 1:
        name = list(sets['region'])[0]
        item = regions[name]
        try:
            region = Region.objects.get(mapbox_id=item['id'])
        except Region.DoesNotExist:
            region, unused = Region.objects.get_or_create(
                name=item['name'], country=country,
                defaults=dict(mapbox_id=item['id']),
            )
        retval['region'] = region

    # Can't do anything with a city without a country
    # (Region is optional, though)
    if country and len(sets['city']) == 1:
        name = list(sets['city'])[0]
        item = cities[name]
        if 'lat' in item and 'lon' in item:
            print('Get or create city: %r' % item)
            try:
                city = City.objects.get(mapbox_id=item['id'])
            except City.DoesNotExist:
                city, created = City.objects.get_or_create(
                    name=item['name'], region=region, country=country,
                    defaults=dict(
                        mapbox_id=item['id'],
                        lat=item['lat'],
                        lng=item['lon'],
                    )
                )
            retval['city'] = city
        else:
            print('NO LAT, LONG for city %s' % item['name'])

    return retval


class Command(BaseCommand):
    args = '(no args)'
    help = 'Geocode users'

    def handle(self, *args, **options):
        print('Here we go!')

        map_id = MAPBOX_MAP_ID

        if not map_id:
            raise Exception('MAPBOX_MAP_ID is not defined')

        # Reset mozillians from some country
        def reset_country(code):
            UserProfile.objects.filter(country=code, geo_coded=True).update(geo_coded=False)
            Geocoding.objects.filter(country=code).delete()

            print('COUNTRIES["%s"] = %r' % (code, COUNTRIES[code]))
            print(repr(country_code_to_mapbox_name(code)))

        # Apply known data from geocoding model
        for item in Geocoding.objects.all():
            item.apply()

        # Now - start looking at profiles we haven't been able to geocode yet
        num_geocoded = 0

        # Only look at profiles that have at least some location data entered
        # and we haven't already geocoded
        qset = UserProfile.objects.filter(geo_country=None).exclude(country='', region='', city='')
        # Skip the stupid ones that are just in there to test for injection attacks
        qset = qset.exclude(city__contains='<')
        print('%d profiles left to geocode...' % qset.count())
        for profile in qset.order_by('country', 'region', 'city'):
            # Profile might have been updated already while we were geocoding a previous user
            profile = UserProfile.objects.get(pk=profile.pk)
            if profile.geo_country:
                continue

            city, region, country = profile.city, profile.region, profile.country

            print('%d: %s, %s, %s' % (profile.pk, city, region, country))

            # Mapbox does better if we use the full name for the country
            if country:
                country = COUNTRIES[country.lower()]

            name = ' '.join([x for x in (city, region, country) if x]).replace('+', '')
            print(repr(name))
            encoded_name = name.encode('utf8')
            quoted_name = urllib.quote_plus(encoded_name, '')
            url = 'http://api.tiles.mapbox.com/v3/%s/geocode/%s.json' % (map_id, quoted_name)
            print(url)
            r = requests.get(url)
            try:
                r.raise_for_status()
            except requests.exceptions.HTTPError as e:
                print(e)
                continue
            data = r.json
            if callable(data):
                data = data()
            results = data['results']
            results = massage_results(profile.country, results)
            if not results:
                print('NO results for %s' % (name,))
                continue
            print('Results: %s' % results.values())
            if 'city' in results:
                profile.geo_city = results['city']
            if 'region' in results:
                profile.geo_region = results['region']
            if 'country' in results:
                profile.geo_country = results['country']
            profile.save()
            count = Geocoding.remember(profile).apply()
            print('Applied geocoding of %s to %d records' % (name, count))

            num_geocoded += 1
            if num_geocoded >= 500:
                break

        print('%d profiles left to geocode.' % (qset.count() - num_geocoded))
