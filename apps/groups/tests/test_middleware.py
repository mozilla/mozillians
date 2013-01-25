from django.core.urlresolvers import reverse
from nose.tools import eq_

from common.tests import ESTestCase


class GroupRedirectionMiddlewareTests(ESTestCase):

    def test_group_redirection_middleware(self):
        """Test the group redirection middleware."""
        self.mozillian_client.get('/')
        response = self.mozillian_client.get(reverse('group', args=['staff']),
                                             follow=True)
        eq_(200, response.status_code)

        response = self.mozillian_client.get('/group/44-invalid-group',
                                             follow=True)
        eq_(404, response.status_code)
