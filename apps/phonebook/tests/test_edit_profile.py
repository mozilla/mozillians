# -*- coding: utf-8 -*-
import os

from django.test.utils import override_settings

from funfactory.urlresolvers import reverse
from nose.tools import eq_

from apps.common.tests import ESTestCase, user

ASSERTION = 'asldkfjasldfka'


@override_settings(AUTHENTICATION_BACKENDS=['common.backends.TestBackend'])
class EditProfileTests(ESTestCase):

    def test_geographic_fields_increasing(self):
        """Geographic fields exist and require increasing specificity."""
        u = user()
        self.client.login(email=u.email, password='testpass')
        data = {'city': 'New York', 'full_name': 'Foobar'}
        url = reverse('profile.edit')
        response = self.client.post(url, data)
        eq_(400, response.status_code)

        data.update({'region': 'New York'})
        response = self.client.post(url, data)
        eq_(400, response.status_code)

        data.update({'country': 'us'})
        response = self.client.post(url, data, follow=True)
        eq_(200, response.status_code)

    def test_invalid_country(self):
        """Not every country is a real country."""
        u = user()
        self.client.login(email=u.email, password='testpass')
        data = {'country': 'xyz', 'full_name': 'Foobar'}
        response = self.client.post(reverse('profile.edit'), data)
        eq_(400, response.status_code)

    def test_unicode_avatar_filename(self):
        filename = os.path.join(os.path.dirname(__file__),
                                'profile-φωτο.jpg')
        with open(filename, 'rb') as f:
            data = {'full_name': 'Mozillian', 'photo': f}
            response = self.mozillian_client.post(reverse('profile.edit'),
                                                  data, follow=True)

        eq_(200, response.status_code)
