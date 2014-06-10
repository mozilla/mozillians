from django.core.urlresolvers import reverse

from mock import patch
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.geo.tests import CountryFactory, RegionFactory, CityFactory
from mozillians.phonebook.forms import ProfileForm
from mozillians.phonebook.tests import _get_privacy_fields
from mozillians.users.managers import MOZILLIANS
from mozillians.users.models import UserProfile
from mozillians.users.tests import UserFactory


class ProfileEditTests(TestCase):

    def test_profile_edit_vouched_links_to_groups_page(self):
        """A vouched user editing their profile is shown a link to the groups page.
        """
        user = UserFactory.create()
        url = reverse('phonebook:profile_edit', prefix='/en-US/')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        groups_url = reverse('groups:index_groups', prefix='/en-US/')
        ok_(groups_url in response.content)

    def test_profile_edit_unvouched_doesnt_link_to_groups_page(self):
        """An unvouched user editing their profile is not shown a link to the groups page.
        """
        user = UserFactory.create(vouched=False)
        url = reverse('phonebook:profile_edit', prefix='/en-US/')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        groups_url = reverse('groups:index_groups', prefix='/en-US/')
        ok_(groups_url not in response.content)

    def test_languages_get_saved(self):
        user = UserFactory.create(email='es@example.com')
        data = {'full_name': user.userprofile.full_name,
                'email': user.email,
                'username': user.username,
                'lat': 40.005814,
                'lng': -3.42071,
                'externalaccount_set-MAX_NUM_FORMS': '1000',
                'externalaccount_set-INITIAL_FORMS': '0',
                'externalaccount_set-TOTAL_FORMS': '0',
                'language_set-0-id': '',
                'language_set-0-userprofile': '',
                'language_set-0-code': 'en',
                'language_set-1-id': '',
                'language_set-1-userprofile': '',
                'language_set-1-code': 'fr',
                'language_set-MAX_NUM_FORMS': '1000',
                'language_set-INITIAL_FORMS': '0',
                'language_set-TOTAL_FORMS': '2',
            }
        data.update(_get_privacy_fields(MOZILLIANS))

        url = reverse('phonebook:profile_edit', prefix='/en-US/')
        with self.login(user) as client:
            response = client.post(url, data=data, follow=True)
        eq_(response.status_code, 200)

        profile = UserProfile.objects.get(pk=user.userprofile.pk)
        eq_(set(profile.language_set.values_list('code', flat=True)), set(['en', 'fr']))

    def test_location_data_required(self):
        user = UserFactory.create(email='latlng@example.com')
        data = {'full_name': user.userprofile.full_name,
                'email': user.email,
                'username': user.username,
                'externalaccount_set-MAX_NUM_FORMS': '1000',
                'externalaccount_set-INITIAL_FORMS': '0',
                'externalaccount_set-TOTAL_FORMS': '0',
                'language_set-MAX_NUM_FORMS': '1000',
                'language_set-INITIAL_FORMS': '0',
                'language_set-TOTAL_FORMS': '0',
            }
        data.update(_get_privacy_fields(MOZILLIANS))

        form = ProfileForm(data=data)
        eq_(form.is_valid(), False)
        ok_(form.errors.get('lat'))
        ok_(form.errors.get('lng'))

    @patch('mozillians.geo.lookup.reverse_geocode')
    def test_location_city_region_optout(self, mock_reverse_geocode):
        country = CountryFactory.create(mapbox_id='country1', name='Petoria')
        region = RegionFactory.create(country=country, mapbox_id='region1', name='Ontario')
        city = CityFactory.create(region=region, mapbox_id='city1', name='Toronto')
        mock_reverse_geocode.return_value = (country, region, city)
        user = UserFactory.create(email='latlng@example.com')
        data = {'full_name': user.userprofile.full_name,
                'email': user.email,
                'username': user.username,
                'lat': 40.005814,
                'lng': -3.42071,
                'externalaccount_set-MAX_NUM_FORMS': '1000',
                'externalaccount_set-INITIAL_FORMS': '0',
                'externalaccount_set-TOTAL_FORMS': '0',
                'language_set-MAX_NUM_FORMS': '1000',
                'language_set-INITIAL_FORMS': '0',
                'language_set-TOTAL_FORMS': '0',
            }
        data.update(_get_privacy_fields(MOZILLIANS))

        form = ProfileForm(data=data)
        eq_(form.is_valid(), True)
        eq_(form.instance.geo_country, country)
        eq_(form.instance.geo_region, None)
        eq_(form.instance.geo_city, None)
