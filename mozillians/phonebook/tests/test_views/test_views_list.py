from django.core.urlresolvers import reverse
from django.test import Client
from funfactory.helpers import urlparams

from mock import patch
from mozillians.geo.tests import CountryFactory, RegionFactory, CityFactory
from nose.tools import eq_

from mozillians.common.tests import TestCase, requires_login, requires_vouch
from mozillians.users.tests import UserFactory


# FIXME: These tests are particularly slow. See if there's any way to improve that.
class ListTests(TestCase):
    @requires_login()
    def test_list_mozillians_in_location_anonymous(self):
        client = Client()
        url = reverse('phonebook:list_country', kwargs={'country': 'Greece'})
        client.get(url, follow=True)

    @requires_vouch()
    def test_list_mozillians_in_location_unvouched(self):
        user = UserFactory.create(vouched=False)
        with self.login(user) as client:
            url = reverse('phonebook:list_country', kwargs={'country': 'Greece'})
            client.get(url, follow=True)

    @patch('mozillians.groups.views.settings.ITEMS_PER_PAGE', 1)
    def test_list_mozillians_in_location_country_vouched(self):
        country = CountryFactory.create()
        country2 = CountryFactory.create()
        user_listed_1 = UserFactory.create(userprofile={'geo_country': country})
        UserFactory.create(userprofile={'geo_country': country})
        UserFactory.create()
        UserFactory.create(vouched=False)
        UserFactory.create(vouched=False, userprofile={'geo_country': country2})
        user = UserFactory.create()
        with self.login(user) as client:
            url = reverse('phonebook:list_country', kwargs={'country': country.name})
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/location_list.html')
        eq_(response.context['country_name'], country.name)
        eq_(response.context['city_name'], None)
        eq_(response.context['region_name'], None)
        eq_(response.context['people'].paginator.count, 2)
        eq_(response.context['people'].paginator.num_pages, 2)
        eq_(response.context['people'].number, 1)
        eq_(response.context['people'].object_list[0],
            user_listed_1.userprofile)

    @patch('mozillians.groups.views.settings.ITEMS_PER_PAGE', 1)
    def test_list_mozillians_in_location_country_second_page(self):
        country = CountryFactory.create()
        UserFactory.create(userprofile={'geo_country': country})
        user_listed_2 = (UserFactory.create(userprofile={'geo_country': country}))
        user = UserFactory.create()
        with self.login(user) as client:
            url = reverse('phonebook:list_country', kwargs={'country': country.name})
            url = urlparams(url, page=2)
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['people'].paginator.count, 2)
        eq_(response.context['people'].paginator.num_pages, 2)
        eq_(response.context['people'].number, 2)
        eq_(response.context['people'].object_list[0],
            user_listed_2.userprofile)

    @patch('mozillians.groups.views.settings.ITEMS_PER_PAGE', 1)
    def test_list_mozillians_in_location_country_empty_page(self):
        country = CountryFactory.create()
        UserFactory.create(userprofile={'geo_country': country})
        UserFactory.create(userprofile={'geo_country': country})
        user = UserFactory.create()
        with self.login(user) as client:
            url = reverse('phonebook:list_country', kwargs={'country': country.name})
            url = urlparams(url, page=20000)
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['people'].number, 2)

    @patch('mozillians.groups.views.settings.ITEMS_PER_PAGE', 1)
    def test_list_mozillians_in_location_country_invalid_page(self):
        country = CountryFactory.create()
        UserFactory.create(userprofile={'geo_country': country})
        UserFactory.create(userprofile={'geo_country': country})
        user = UserFactory.create()
        with self.login(user) as client:
            url = reverse('phonebook:list_country', kwargs={'country': country.name})
            url = urlparams(url, page='invalid')
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['people'].number, 1)

    def test_list_mozillians_in_location_region_vouched(self):
        country = CountryFactory.create()
        country2 = CountryFactory.create()
        region = RegionFactory.create(country=country)
        region2 = RegionFactory.create(country=country)
        user_listed = UserFactory.create(
            userprofile={'geo_country': country,
                         'geo_region': region})
        UserFactory.create(
            userprofile={'geo_country': country,
                         'geo_region': region2})
        UserFactory.create()
        UserFactory.create(vouched=False)
        UserFactory.create(vouched=False, userprofile={'geo_country': country2})
        user = UserFactory.create()
        with self.login(user) as client:
            url = reverse(
                'phonebook:list_region',
                kwargs={'country': country.name, 'region': region.name})
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/location_list.html')
        eq_(response.context['country_name'], country.name)
        eq_(response.context['city_name'], None)
        eq_(response.context['region_name'], region.name)
        eq_(response.context['people'].paginator.count, 1)
        eq_(response.context['people'].object_list[0], user_listed.userprofile)

    def test_list_mozillians_in_location_city_vouched(self):
        country = CountryFactory.create()
        country2 = CountryFactory.create()
        city = CityFactory(country=country)
        city2 = CityFactory(country=country)
        user_listed = UserFactory.create(
            userprofile={'geo_country': country,
                         'geo_city': city})
        UserFactory.create(
            userprofile={'geo_country': country,
                         'geo_city': city2})
        UserFactory.create()
        UserFactory.create(vouched=False)
        UserFactory.create(vouched=False, userprofile={'geo_country': country2})
        user = UserFactory.create()
        with self.login(user) as client:
            url = reverse('phonebook:list_city',
                          kwargs={'country': country.name, 'city': city.name})
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/location_list.html')
        eq_(response.context['country_name'], country.name)
        eq_(response.context['city_name'], city.name)
        eq_(response.context['region_name'], None)
        eq_(response.context['people'].paginator.count, 1)
        eq_(response.context['people'].object_list[0], user_listed.userprofile)

    def test_list_mozillians_in_location_region_n_city_vouched(self):
        country = CountryFactory.create()
        country2 = CountryFactory.create()
        region = RegionFactory.create(country=country)
        city = CityFactory(country=country, region=region)
        city2 = CityFactory(country=country)
        user_listed = UserFactory.create(
            userprofile={'geo_country': country,
                         'geo_region': region,
                         'geo_city': city})
        UserFactory.create(
            userprofile={'geo_country': country,
                         'geo_region': region,
                         'geo_city': city2})
        UserFactory.create()
        UserFactory.create(vouched=False)
        UserFactory.create(vouched=False, userprofile={'geo_country': country2})
        user = UserFactory.create()
        with self.login(user) as client:
            url = reverse('phonebook:list_region_city',
                          kwargs={'country': country.name, 'region': region.name,
                                  'city': city.name})
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/location_list.html')
        eq_(response.context['country_name'], country.name)
        eq_(response.context['city_name'], city.name)
        eq_(response.context['region_name'], region.name)
        eq_(response.context['people'].paginator.count, 1)
        eq_(response.context['people'].object_list[0], user_listed.userprofile)

    def test_list_mozillians_in_location_invalid_country(self):
        user = UserFactory.create()
        with self.login(user) as client:
            url = reverse('phonebook:list_country',
                          kwargs={'country': 'invalid'})
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'phonebook/location_list.html')
        eq_(response.context['country_name'], 'invalid')
        eq_(response.context['city_name'], None)
        eq_(response.context['region_name'], None)
        eq_(response.context['people'].paginator.count, 0)
