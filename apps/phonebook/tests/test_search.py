from funfactory.urlresolvers import reverse
from nose.tools import eq_
from pyquery import PyQuery as pq

from apps.common.tests import ESTestCase
from apps.users.models import UserProfile
from apps.groups.models import Group

from ..tests import user, create_client


class TestSearch(ESTestCase):

    def test_search_with_space(self):
        """Extra spaces should not impact search queries."""
        amanda = 'Amanda Younger'
        amandeep = 'Amandeep McIlrath'

        # Create a group to test searching for groups
        Group.objects.create(name='spam', auto_complete=True)
        Group.objects.create(name='jam', auto_complete=True)
        Group.objects.create(name='bread', auto_complete=True)

        url = reverse('search')
        r = self.mozillian_client.get(url, {'q': 'am'})

        eq_(r.status_code, 200)
        peeps = r.context['people']
        saw_amanda = saw_amandeep = False

        for person in peeps:
            if person.display_name == amanda:
                saw_amanda = True
            elif person.display_name == amandeep:
                saw_amandeep = True
            if saw_amanda and saw_amandeep:
                break

        self.assertTrue(saw_amanda, 'We see first person')
        self.assertTrue(saw_amandeep, 'We see another person')

        # Assert appropriate group names are found in the document
        self.assertContains(r, 'spam')
        self.assertContains(r, 'jam')
        self.assertNotContains(r, 'bread')

    def test_nonvouched_search(self):
        """Make sure that only non vouched users are returned on
        search.

        """
        amanda = 'Amanda Younger'
        amandeep = 'Amandeep McIlrath'

        user(full_name='Amanda Unvouched')


        url = reverse('search')
        r = self.mozillian_client.get(url, {'q': 'Am'})
        rnv = self.mozillian_client.get(url, {'q': 'Am', 'nonvouched_only': 1})

        eq_(r.status_code, 200)
        peeps = r.context['people']
        peeps_nv = rnv.context['people']

        saw_amanda = saw_amandeep = False

        for person in peeps:
            if person.display_name == amandeep:
                assert person.is_vouched, 'Amanda is a Mozillian'
                saw_amandeep = True
            elif person.display_name == amanda:
                if person.is_vouched:
                    self.fail('Amandeep should have pending status')
                saw_amanda = True
            if saw_amanda and saw_amandeep:
                break

        assert amanda in [p.display_name for p in peeps_nv]
        self.assertTrue(saw_amanda, 'We see vouched users')
        self.assertTrue(saw_amandeep, 'We see non-vouched users')
        assert all(not person.is_vouched for person in peeps_nv)

    def test_profilepic_search(self):
        """Make sure searching for only users with profile pics works."""

        user(full_name='Aman', vouched=True, photo=True)
        user(full_name='Amanda', vouched=True, photo=True)
        u = user(full_name='Amihuman', vouched=True)

        self.client.login(email=u.email)

        url = reverse('search')

        r_pics_only = self.client.get(url, {'q': 'Am', 'picture_only': 1})
        eq_(r_pics_only.status_code, 200)
        pics_only_peeps = r_pics_only.context['people']
        for person in pics_only_peeps:
            assert person.photo, 'Every person should have a photo'

        r = self.client.get(url, {'q': 'Am'})
        eq_(r.status_code, 200)
        peeps = r.context['people']
        # Make sure u shows up in normal search
        assert u in [p.user for p in peeps]
        # Make sure u doesn't show up in picture only search
        assert u not in [p.user for p in pics_only_peeps]

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

    def test_proper_url_arg_handling(self):
        """Make sure URL arguments are handled correctly."""
        # Create a new unvouched user to ensure results show up in search view
        user()

        search_url = reverse('search')
        r = self.mozillian_client.get(search_url)
        assert not pq(r.content)('.result')

        r = self.mozillian_client.get(search_url,
                                      {'q': u'', 'nonvouched_only': 1})

        assert pq(r.content)('.result')

    def test_single_result(self):
        """Makes sure the client is redirected to the users page if
        they are the only result returned by the query.

        """
        u = user(full_name='Findme Ifyoucan')

        r = create_client(vouched=True).get(reverse('search'),
                                            {'q': 'Fin', 'nonvouched_only': 1},
                                                 follow=True)

        eq_(r.status_code, 200, 'Search view query should return 200')

        eq_(u.get_profile().display_name,
            pq(r.content)('#profile-info h2').text(),
            'Should be redirected to a user with the right name')
