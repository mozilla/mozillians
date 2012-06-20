from django.test.utils import override_settings

from funfactory.urlresolvers import reverse
from nose.tools import eq_

from common.tests import TestCase, user

ASSERTION = 'asldkfjasldfka'

@override_settings(AUTHENTICATION_BACKENDS=('common.backends.TestBackend',))
class EditProfileTests(TestCase):

    def test_geographic_fields_increasing(self):
        """Geographic fields exist and require increasing specificity."""
        u = user()
        self.client.login(email=u.email, password='testpass')
        # For some reason last_name is a required field.
        data = {'city': 'New York', 'last_name': 'Foobar'}
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
        data = {'country': 'xyz', 'last_name': 'Foobar'}
        response = self.client.post(reverse('profile.edit'), data)
        eq_(400, response.status_code)
