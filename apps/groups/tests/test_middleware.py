from django.core.urlresolvers import reverse
from nose.tools import eq_

from apps.common.tests.init import ESTestCase

from ..models import Group, GroupAlias


class GroupRedirectionMiddlewareTests(ESTestCase):

    def test_oldgroup_redirection_middleware(self):
        """Test the group old url schema redirection middleware."""
        self.mozillian_client.get('/')
        response = self.mozillian_client.get(reverse('group', args=['staff']),
                                             follow=True)
        eq_(200, response.status_code)

        response = self.mozillian_client.get('/group/44-invalid-group',
                                             follow=True)
        eq_(404, response.status_code)

    def test_group_alias_redirection_middleware(self):
        """Test GroupAlias redirection middleware."""
        staff_group = Group.objects.get(name='staff')
        GroupAlias.objects.create(name='ffats', url='ffats', alias=staff_group)
        response = self.mozillian_client.get(reverse('group', args=['ffats']))
        eq_(301, response.status_code)
