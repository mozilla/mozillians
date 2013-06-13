from time import sleep

from funfactory.helpers import urlparams
from funfactory.urlresolvers import reverse
from nose.tools import eq_
from pyquery import PyQuery as pq

from apps.common.tests.init import ESTestCase
from apps.users.models import MOZILLIANS, PUBLIC, S, UserProfile
from apps.groups.models import Group

from ..tests import user, create_client


class TestSearch(ESTestCase):

    def test_search_with_space(self):
        """Extra spaces should not impact search queries."""
        # Create a group to test searching for groups
        Group.objects.create(name='spam', auto_complete=True)
        Group.objects.create(name='jam', auto_complete=True)
        Group.objects.create(name='bread', auto_complete=True)

        url = reverse('search')
        response = self.mozillian_client.get(url, {'q': 'am'})

        eq_(response.status_code, 200)

        queryset = response.context['people'].object_list
        for up in [self.mozillian.userprofile, self.mozillian2.userprofile]:
            self.assertTrue(up in queryset)

        # Assert appropriate group names are found in the document
        self.assertContains(response, 'spam')
        self.assertContains(response, 'jam')
        self.assertNotContains(response, 'bread')

    def test_nonvouched_search(self):
        """Make sure that only non vouched users are returned on
        search.

        """
        url = reverse('search')
        response = self.mozillian_client.get(url)
        eq_(response.status_code, 200)
        eq_(len(response.context['people']), 2)

        response = self.mozillian_client.get(
            url, {'q': 'Am', 'include_non_vouched': 1})
        eq_(response.status_code, 200)
        eq_(len(response.context['people']), 3)

    def test_mozillian_search_pagination(self):
        """Tests the pagination on search.

        1. assumes no page is passed, but valid limit is passed
        2. assumes invalid page is passed, no limit is passed
        3. assumes valid page is passed, no limit is passed
        4. assumes valid page is passed, valid limit is passed
        """
        url = reverse('search')
        r = self.mozillian_client.get(url, {'q': 'Amand', 'limit': '1'})
        peeps = r.context['people']
        self.assertEqual(len(peeps), 1)

        r = self.mozillian_client.get(url, {'q': 'Amand', 'page': 'test'})
        peeps = r.context['people']
        self.assertEqual(len(peeps), 2)

        r = self.mozillian_client.get(url, {'q': 'Amand', 'page': '1'})
        peeps = r.context['people']
        self.assertEqual(len(peeps), 2)

        r = self.mozillian_client.get(url, {'q': 'Amand', 'page': 'test',
                                                'limit': '1'})
        peeps = r.context['people']
        self.assertEqual(len(peeps), 1)

        r = self.mozillian_client.get(url, {'q': 'Amand', 'page': 'test',
                                                'limit': 'x'})
        peeps = r.context['people']
        self.assertEqual(len(peeps), 2)

        r = self.mozillian_client.get(url, {'q': 'Amand', 'page': 'test',
                                            'limit': '-3'})
        peeps = r.context['people']
        self.assertEqual(len(peeps), 2)

    def test_empty_query_search(self):
        """Make sure the search method works with an empty query."""
        assert UserProfile.search('').count()

    def test_single_result(self):
        """Makes sure the client is redirected to the users page if
        they are the only result returned by the query.

        """
        u = user(full_name='Findme Ifyoucan')

        r = create_client(vouched=True).get(
            reverse('search'), {'q': 'Fin', 'include_non_vouched': 1},
            follow=True)

        eq_(r.status_code, 200, 'Search view query should return 200')

        eq_(u.get_profile().display_name,
            pq(r.content)('h1.fn').text(),
            'Should be redirected to a user with the right name')

    def test_public_search_vouched(self):
        response = self.anonymous_client.get(reverse('search'), follow=True)
        profile = response.context['profile']
        eq_(profile, self.mozillian2.userprofile)
        eq_(profile._privacy_level, PUBLIC)

    def test_public_search_with_unvouched(self):
        url = urlparams(reverse('search'), include_non_vouched='on')
        response = self.anonymous_client.get(url, follow=True)
        paginator = response.context['people'].paginator
        eq_(paginator.count, 2)
        self.assertIn(self.mozillian2.userprofile, paginator.object_list)
        self.assertIn(self.pending.userprofile, paginator.object_list)

    def test_removal_from_public_index(self):
        """Test that a user gets removed from public index if makes
        profile mozillians only again.

        """
        before = (S(UserProfile)
                  .indexes(UserProfile.get_index(public_index=True))
                  .count())
        profile = self.mozillian2.userprofile
        profile.privacy_full_name = MOZILLIANS
        profile.save()
        sleep(1)
        after = (S(UserProfile)
                 .indexes(UserProfile.get_index(public_index=True))
                 .count())
        eq_(after+1, before)
