from django.core.urlresolvers import reverse

from nose.tools import eq_

from mozillians.common.tests import TestCase
from mozillians.groups.tests import GroupFactory
from mozillians.users.tests import UserFactory


class OldGroupRedirectionMiddlewareTests(TestCase):
    def setUp(self):
        self.user = UserFactory.create()

    def test_valid_name(self):
        """Valid group with name that matches the old group regex doens't redirect."""
        group = GroupFactory.create(name='111-foo')
        GroupFactory.create(name='foo')
        url = reverse('groups:show_group', kwargs={'url': group.url})
        with self.login(self.user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['group'], group)

    def test_old_group_url_redirects(self):
        group = GroupFactory.create()
        url = '/group/111-{0}/'.format(group.url)
        with self.login(self.user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['group'], group)

    def test_not_existing_group_404s(self):
        url = '/group/111-invalid/'
        with self.login(self.user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 404)
