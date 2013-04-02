from django.core.urlresolvers import reverse
from nose.tools import eq_

from apps.common.tests.init import ESTestCase
from apps.common.decorators import allow_public, allow_unvouched


class TestDecorators(ESTestCase):

    def test_allow_public_decorator(self):

        def foo():
            pass

        eq_(getattr(foo, '_allow_public', None), None)
        allow_public(foo)
        self.assertTrue(foo._allow_public)

    def test_allow_unvouched_decorator(self):

        def foo():
            pass
        eq_(getattr(foo, '_allow_unvouched', None), None)
        allow_unvouched(foo)
        self.assertTrue(foo._allow_unvouched)


class TestStrongholdMiddleware(ESTestCase):
    """Stronghold Testcases."""
    urls = 'apps.common.tests.test_urls'

    def test_stronghold(self):
        """Test stronhold middleware functionality."""
        self.excepted_results = {
            'vouched': {'vouched': True, 'unvouched': False, 'public': False},
            'unvouched': {'vouched': True, 'unvouched': True, 'public': False},
            'public': {'vouched': True, 'unvouched': True, 'public': True},
            'excepted': {'vouched': True, 'unvouched': True, 'public': True}}

        self.clients = {
            'vouched': self.mozillian_client,
            'unvouched': self.pending_client,
            'public': self.client}

        for url in self.excepted_results:
            for user, client in self.clients.items():
                r_url = reverse(url, prefix='/en-US/')
                response = client.get(r_url, follow=True)
                if self.excepted_results[url][user]:
                    eq_(response.content, 'Hi!')

                else:
                    eq_(len(response.redirect_chain), 2)
                    eq_(len(response.context['messages']), 1)
