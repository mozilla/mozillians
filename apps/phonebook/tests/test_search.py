import os

from django.conf import settings

from nose.tools import eq_
from pyquery import PyQuery as pq

from common.tests import ESTestCase
from elasticutils import get_es
from funfactory.urlresolvers import reverse

from users.models import UserProfile


class TestSearch(ESTestCase):
    def test_search_with_space(self):
        """Extra spaces should not impact search queries."""
        amanda = 'Amanda Younger'
        amandeep = 'Amandeep McIlrath'
        url = reverse('search')
        r = self.mozillian_client.get(url, dict(q='Am'))
        rs = self.mozillian_client.get(url, dict(q=' Am'))

        eq_(r.status_code, 200)
        peeps = r.context['people']
        peeps_ws = rs.context['people']
        saw_amanda = saw_amandeep = False

        for person in peeps:
            if person.display_name == amanda:
                saw_amanda = True
            elif person.display_name == amandeep:
                saw_amandeep = True
            if saw_amanda and saw_amandeep:
                break

        assert peeps[0].id in (peeps_ws[0].id, peeps_ws[1].id)
        self.assertTrue(saw_amanda, 'We see first person')
        self.assertTrue(saw_amandeep, 'We see another person')

    def test_nonvouched_search(self):
        """Make sure that only non vouched users are returned on search."""
        amanda = 'Amanda Younger'
        amandeep = 'Amandeep McIlrath'
        url = reverse('search')
        r = self.mozillian_client.get(url, dict(q='Am'))
        rnv = self.mozillian_client.get(url, dict(q='Am', nonvouched_only=1))

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

        self.assertEqual(peeps_nv[0].display_name, amanda)
        self.assertTrue(saw_amanda, 'We see vouched users')
        self.assertTrue(saw_amandeep, 'We see non-vouched users')
        assert all(not person.is_vouched for person in peeps_nv)

    def test_profilepic_search(self):
        """Make sure searching for only users with profile pics works."""
        with open(os.path.join(os.path.dirname(__file__), 'profile-photo.jpg')) as f:
            r = self.mozillian_client.post(reverse('profile.edit'),
                dict(first_name='Aman', last_name='Withapic', photo=f))

        if not settings.ES_DISABLED:
            get_es().refresh(settings.ES_INDEXES['default'], timesleep=0)

        amanhasapic = 'Aman Withapic'
        amanda = 'Amanda Younger'
        url = reverse('search')
        r = self.mozillian_client.get(url, dict(q='Am'))
        rpp = self.mozillian_client.get(url, dict(q='Am', picture_only=1))

        eq_(r.status_code, 200)
        peeps = r.context['people']
        peeps_pp = rpp.context['people']
        saw_amanda = False

        # Make sure that every body has a profile picture
        for person in peeps:
            if person.display_name == amanda:
                if bool(person.photo):
                    self.fail('Amanda doesnt have a profile pic')
                saw_amanda = True

        # Make sure amanda shows up in peeps
        assert amanda in [p.display_name for p in peeps]
        # Make sure she doesn't show up in peeps_pp
        assert amanda not in [p.display_name for p in peeps_pp]
        self.assertEqual(peeps_pp[0].display_name, amanhasapic)
        self.assertTrue(saw_amanda, 'We dont see profile picture')

    def test_mozillian_search_pagination(self):
        """Tests the pagination on search.

        1. assumes no page is passed, but valid limit is passed
        2. assumes invalid page is passed, no limit is passed
        3. assumes valid page is passed, no limit is passed
        4. assumes valid page is passed, valid limit is passed
        """
        url = reverse('search')
        r = self.mozillian_client.get(url, dict(q='Amand', limit='1'))
        peeps = r.context['people']
        self.assertEqual(len(peeps), 1)

        r = self.mozillian_client.get(url, dict(q='Amand', page='test'))
        peeps = r.context['people']
        self.assertEqual(len(peeps), 2)

        r = self.mozillian_client.get(url, dict(q='Amand', page='1'))
        peeps = r.context['people']
        self.assertEqual(len(peeps), 2)

        r = self.mozillian_client.get(url, dict(q='Amand', page='test',
                                                limit='1'))
        peeps = r.context['people']
        self.assertEqual(len(peeps), 1)

        r = self.mozillian_client.get(url, dict(q='Amand', page='test',
                                                limit='x'))
        peeps = r.context['people']
        self.assertEqual(len(peeps), 2)

        r = self.mozillian_client.get(url, dict(q='Amand', page='test',
                                                limit='-3'))
        peeps = r.context['people']
        self.assertEqual(len(peeps), 2)

    def test_empty_query_search(self):
        """Make sure the search method works with an empty query"""
        assert UserProfile.search('').count()

    def test_proper_url_arg_handling(self):
        search_url = reverse('search')
        r = self.mozillian_client.get(search_url)
        assert not pq(r.content)('.result')

        r = self.mozillian_client.get(search_url,
                                      dict(q=u'', nonvouched_only=1))
        assert pq(r.content)('.result')
