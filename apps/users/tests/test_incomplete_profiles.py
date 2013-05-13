from django.core.urlresolvers import reverse

from mock import patch
from nose.tools import eq_

from apps.common.tests.init import ESTestCase, user
from apps.groups.models import Group


class IncompleteProfiles(ESTestCase):
    """Test incomplete profiles."""

    @patch('apps.users.models.index_objects.delay')
    def test_not_index(self, mock_obj):
        """Test incomplete profiles indexing."""
        user()
        self.assertFalse(mock_obj.called, 'Incomplete profile get indexed')

    def test_no_profile_page(self):
        """Test incomplete profile no profile page."""
        u = user()
        response = self.mozillian_client.get(
            reverse('profile', kwargs={'username': u.username}),
            follow=True)
        eq_(response.status_code, 404,
            'Incomplete profile has a profile page.')

    def test_not_list(self):
        """Test incomplete profile group listing."""
        u = user()
        u.userprofile.groups.add(Group.objects.get(name='staff'))
        response = self.mozillian_client.get(
            reverse('group', kwargs={'url': 'staff'}), follow=True)
        eq_(len(response.context['people']), 0,
            'Mozillians with incomplete profile get listed in groups.')
