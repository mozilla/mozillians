from nose.tools import eq_

from common.tests import TestCase
from funfactory.urlresolvers import reverse


class TrailingSlashMiddlewareTestCase(TestCase):
    def test_strip_trailing_slash(self):
        url = reverse('about')
        r = self.client.get(url + '/')
        self.assertRedirects(r, url, status_code=301)

    def test_no_trailing_slash(self):
        """Don't redirect 404s without a trailing slash."""
        # Need to use loged in client because other wise we try to log you in.
        r = self.mozillian_client.get('/en-US/ohnoez')
        eq_(404, r.status_code, '/ohnoez should be a 404.')
