import os
from django.core.urlresolvers import reverse
from django.test.utils import override_script_prefix

from mock import patch
from nose.tools import eq_, ok_

from cities_light.models import Country

from mozillians.common.tests import TestCase
from mozillians.phonebook.tests import _get_privacy_fields
from mozillians.users.managers import MOZILLIANS
from mozillians.users.models import UserProfile
from mozillians.users.tests import UserFactory


class ProfileEditTests(TestCase):

    def setUp(self):
        os.environ['NORECAPTCHA_TESTING'] = 'True'

    def test_profile_edit_vouched_links_to_groups_page(self):
        """A vouched user editing their profile is shown a link to the groups page.
        """
        user = UserFactory.create()
        with override_script_prefix('/en-US/'):
            url = reverse('phonebook:profile_edit')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        with override_script_prefix('/en-US/'):
            groups_url = reverse('groups:index_groups')
        ok_(groups_url in unicode(response.content, 'utf-8'))

    def test_profile_edit_unvouched_doesnt_link_to_groups_page(self):
        """An unvouched user editing their profile is not shown a link to the groups page.
        """
        user = UserFactory.create(vouched=False)
        with override_script_prefix('/en-US/'):
            url = reverse('phonebook:profile_edit')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        with override_script_prefix('/en-US/'):
            groups_url = reverse('groups:index_groups')
        ok_(groups_url not in unicode(response.content, 'utf-8'))

    def test_section_does_not_exist(self):
        """When not section exists in request.POST, 404 is raised."""
        user = UserFactory.create(vouched=False)
        with override_script_prefix('/en-US/'):
            url = reverse('phonebook:profile_edit')
        data = {
            'full_name': user.userprofile.full_name,
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
        with self.login(user) as client:
            response = client.post(url, data=data, follow=True)
        eq_(response.status_code, 404)

    def test_wrong_section(self):
        """When a wrong section is given in request.POST, 404 is raised."""
        user = UserFactory.create(vouched=False)
        with override_script_prefix('/en-US/'):
            url = reverse('phonebook:profile_edit')
        data = {
            'full_name': user.userprofile.full_name,
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
            'foo_section': '',
        }

        data.update(_get_privacy_fields(MOZILLIANS))
        with self.login(user) as client:
            response = client.post(url, data=data, follow=True)
        eq_(response.status_code, 404)

    def test_languages_get_saved(self):
        user = UserFactory.create(email='es@example.com')
        data = {
            'full_name': user.userprofile.full_name,
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
            'languages_section': ''
        }
        data.update(_get_privacy_fields(MOZILLIANS))

        with override_script_prefix('/en-US/'):
            url = reverse('phonebook:profile_edit')
        with self.login(user) as client:
            response = client.post(url, data=data, follow=True)
        eq_(response.status_code, 200)

        profile = UserProfile.objects.get(pk=user.userprofile.pk)
        eq_(set(profile.language_set.values_list('code', flat=True)), set(['en', 'fr']))

    @patch('mozillians.phonebook.views.messages.info')
    def test_succesful_registration(self, info_mock):
        user = UserFactory.create(first_name='', last_name='')
        ok_(not UserProfile.objects.filter(full_name='foo bar').exists())
        country = Country.objects.get(name='Greece')

        with override_script_prefix('/en-US/'):
            url = reverse('phonebook:profile_edit')
        data = {
            'full_name': 'foo bar',
            'email': 'foo@example.com',
            'username': 'foobar',
            'country': country.id,
            'optin': True,
            'registration_section': '',
            'g-recaptcha-response': 'PASSED'
        }
        data.update(_get_privacy_fields(MOZILLIANS))
        with self.login(user) as client:
            response = client.post(url, data, follow=True)

        eq_(response.status_code, 200)
        ok_(info_mock.called)
        ok_(UserProfile.objects.get(full_name='foo bar'))

        def tearDown(self):
            del os.environ['NORECAPTCHA_TESTING']
