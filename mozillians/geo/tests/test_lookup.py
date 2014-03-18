from django.test.utils import override_settings

from mock import patch
from mozillians.geo.models import Country, Region, City
from mozillians.geo.tests import CountryFactory, RegionFactory, CityFactory
from nose.tools import eq_, ok_
from requests import HTTPError

from mozillians.common.tests import TestCase
from mozillians.geo.lookup import reverse_geocode, get_first_mapbox_geocode_result, \
    result_to_country_region_city, result_to_country, result_to_region, result_to_city


@patch('mozillians.geo.lookup.requests')
class TestCallingGeocode(TestCase):
    def test_raise_on_error(self, mock_requests):
        mock_requests.get.return_value.raise_for_status.side_effect = HTTPError
        with self.assertRaises(HTTPError):
            get_first_mapbox_geocode_result('')

    def test_url(self, mock_requests):
        lng = lat = 1.0
        map_id = 'fake.map.id'
        with override_settings(MAPBOX_MAP_ID=map_id):
            get_first_mapbox_geocode_result('1.0,1.0')
        expected_url = 'http://api.tiles.mapbox.com/v3/%s/geocode/%s,%s.json' % (map_id, lng, lat)
        mock_requests.get.assert_called_with(expected_url)


@patch('mozillians.geo.lookup.result_to_country_region_city')
@patch('mozillians.geo.lookup.get_first_mapbox_geocode_result')
class TestReverseGeocode(TestCase):
    def test_empty(self, mock_get_result, mock_result_to_country):
        # If get result returns nothing, reverse_geocode returns Nones
        mock_get_result.return_value = {}
        eq_((None, None, None), reverse_geocode(0.0, 0.0))
        ok_(not mock_result_to_country.called)

    def test_results(self, mock_get_result, mock_result_to_country):
        # If any result, calls result_to_country_region_city
        mock_get_result.return_value = {'foo': 1}
        mock_result_to_country.return_value = (1, 2, 3)
        eq_((1, 2, 3), reverse_geocode(0.0, 0.0))
        mock_result_to_country.assert_called_with(mock_get_result.return_value)


class TestResultToCountryRegionCity(TestCase):
    @patch('mozillians.geo.lookup.result_to_country')
    def test_no_country(self, mock_result_to_country):
        # If result_to_country returns None, None, None
        mock_result_to_country.return_value = None
        eq_((None, None, None), result_to_country_region_city({'foo': 1}))

    @patch('mozillians.geo.lookup.result_to_country')
    @patch('mozillians.geo.lookup.result_to_region')
    def test_country(self, mock_result_to_region, mock_result_to_country):
        # If country in results, builds a Country object, passes result to result_to_region
        result = {
            'country': {'id': 'mapbox_id', 'name': 'Petoria'},
        }
        mock_result_to_country.return_value = CountryFactory.create(mapbox_id='mapbox_id',
                                                                    name='Petoria')
        mock_result_to_region.return_value = None
        country, region, city = result_to_country_region_city(result)
        ok_(region is None)
        ok_(city is None)
        ok_(country is not None)
        ok_(isinstance(country, Country))
        eq_('mapbox_id', country.mapbox_id)
        eq_('Petoria', country.name)
        mock_result_to_region.assert_called_with(result, country)


class TestResultToCountry(TestCase):
    def test_no_country(self):
        eq_(None, result_to_country({'foo': 1}))

    def test_with_country(self):
        result = {'country': {'id': 'mapbox_id', 'name': 'Petoria'}}
        country = result_to_country(result)
        ok_(country is not None)
        ok_(isinstance(country, Country))
        eq_('mapbox_id', country.mapbox_id)
        eq_('Petoria', country.name)

    def test_update_country_name(self):
        # If country name has changed, we update our database
        country = CountryFactory.create()
        # Mapbox returns same country ID, but new improved country name
        new_name = 'Democratic Republic of %s' % country.name
        result = {'country': {'id': country.mapbox_id,
                              'name': new_name}}
        country = result_to_country(result)
        country = Country.objects.get(pk=country.pk)
        eq_(new_name, country.name)


class TestResultToRegion(TestCase):
    def test_no_region(self):
        country = CountryFactory.create()
        eq_(None, result_to_region({}, country))

    def test_with_region(self):
        country = CountryFactory.create()
        result = {
            'province': {
                'name': 'NC',
                'id': 'ID'
            }
        }
        region = result_to_region(result, country)
        eq_('NC', region.name)
        eq_('ID', region.mapbox_id)
        eq_(country, region.country)

    def test_update_name(self):
        # If region name has changed, we update our database
        country = CountryFactory.create()
        region = RegionFactory.create(country=country)
        new_name = "New %s" % region.name
        result = {
            'province': {
                'name': new_name,
                'id': region.mapbox_id,
            }
        }
        result_to_region(result, country)
        region = Region.objects.get(pk=region.pk)
        eq_(new_name, region.name)


class TestResultToCity(TestCase):
    def test_no_city(self):
        eq_(None, result_to_city({}, None, None))

    def test_with_city(self):
        country = CountryFactory.create()
        region = RegionFactory.create(country=country)
        result = {
            'city': {
                'name': 'Carrboro',
                'id': '1234',
                'lat': 0.0,
                'lon': 0.0,
            }
        }
        city = result_to_city(result, country, region)
        eq_('Carrboro', city.name)
        eq_('1234', city.mapbox_id)
        eq_(region, city.region)
        eq_(country, city.country)

    def test_without_region(self):
        # region can be None
        country = CountryFactory.create()
        region = None
        result = {
            'city': {
                'name': 'Carrboro',
                'id': '1234',
                'lat': 0.0,
                'lon': 0.0,
            }
        }
        city = result_to_city(result, country, region)
        eq_('Carrboro', city.name)
        eq_('1234', city.mapbox_id)
        eq_(region, city.region)
        eq_(country, city.country)

    def test_update_name(self):
        city = CityFactory.create()
        new_name = 'New %s' % city.name
        result = {
            'city': {
                'name': new_name,
                'id': city.mapbox_id,
                'lat': city.lat,
                'lon': city.lng,
            }
        }
        result_to_city(result, city.country, None)
        city = City.objects.get(pk=city.pk)
        eq_(new_name, city.name)
