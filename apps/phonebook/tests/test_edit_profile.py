# -*- coding: utf-8 -*-
import os

from django.test.utils import override_settings

from funfactory.urlresolvers import reverse
from nose.tools import eq_

from apps.common.tests.init import ESTestCase

ASSERTION = 'asldkfjasldfka'


@override_settings(AUTHENTICATION_BACKENDS=['common.backends.TestBackend'])
class EditProfileTests(ESTestCase):

    def test_geographic_fields_increasing(self):
        """Geographic fields exist and require increasing specificity."""
        data = self.data_privacy_fields.copy()
        data.update({'city': 'New York', 'full_name': 'Foobar'})
        url = reverse('profile.edit')
        response = self.mozillian_client.post(url, data)
        eq_(400, response.status_code)

        data.update({'region': 'New York'})
        response = self.mozillian_client.post(url, data)
        eq_(400, response.status_code)

        data.update({'country': 'us'})
        response = self.mozillian_client.post(url, data, follow=True)
        eq_(200, response.status_code)

    def test_geographic_fields_without_region(self):
        """Sets a city and a country, but no region."""
        data = self.data_privacy_fields.copy()
        data.update({'city': 'New York', 'country': 'us', 'full_name': 'Foobar'})
        url = reverse('profile.edit')
        response = self.mozillian_client.post(url, data)
        eq_(200, response.status_code)

    def test_invalid_country(self):
        """Not every country is a real country."""
        data = {'country': 'xyz', 'full_name': 'Foobar'}
        response = self.mozillian_client.post(reverse('profile.edit'), data)
        eq_(400, response.status_code)

    def test_unicode_avatar_filename(self):
        filename = os.path.join(os.path.dirname(__file__),
                                'profile-φωτο.jpg')
        with open(filename, 'rb') as f:
            data = self.data_privacy_fields.copy()
            data.update({'full_name': 'Mozillian', 'country': 'pl', 'photo': f})
            response = self.mozillian_client.post(reverse('profile.edit'),
                                                  data, follow=True)

        eq_(200, response.status_code)
