from funfactory.urlresolvers import reverse
from pyquery import PyQuery as pq

from phonebook.tests import LDAPTestCase


class TestSearchBox(LDAPTestCase):
    """Verify that the right users see the searchbox."""

    def test_searchbox(self):
        url = reverse('home')
        r = self.client.get(url)
        doc = pq(r.content)
        assert not doc('input[type=search]')
        r = self.pending_client.get(url)
        doc = pq(r.content)
        assert not doc('input[type=search]')
        r = self.mozillian_client.get(url)
        doc = pq(r.content)
        assert doc('input[type=search]')
