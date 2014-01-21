from django.core.urlresolvers import reverse

from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.users.tests import UserFactory


class ProfileEditTests(TestCase):

    def test_profile_edit_vouched_links_to_groups_page(self):
        """A vouched user editing their profile is shown a link to the groups page.
        """
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('phonebook:profile_edit', prefix='/en-US/')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        groups_url = reverse('groups:index_groups', prefix='/en-US/')
        ok_(groups_url in response.content)

    def test_profile_edit_unvouched_doesnt_link_to_groups_page(self):
        """An unvouched user editing their profile is not shown a link to the groups page.
        """
        user = UserFactory.create(userprofile={'is_vouched': False})
        url = reverse('phonebook:profile_edit', prefix='/en-US/')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        groups_url = reverse('groups:index_groups', prefix='/en-US/')
        ok_(groups_url not in response.content)
