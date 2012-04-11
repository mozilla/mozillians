from django.contrib.auth.models import User

from funfactory.urlresolvers import reverse
from nose.tools import eq_
from pyquery import PyQuery as pq

import common.tests
from locations.models import Country


class TestLocations(common.tests.TestCase):

    def test_empty_location_doesnt_appear(self):
        """Verify an empty location doesn't appear in a user's profile."""
        self.client.login(email=self.mozillian.email)

        canada, created = Country.objects.get_or_create(code='ca')
        r = self.client.post(reverse('profile.edit'),
                dict(last_name='Picnicface'), follow=True)
        doc = pq(r.content)

        assert doc('#profile-info'), ('User should be on their profile '
                                      'page after submitting the form.')
        assert not doc('dd a.location'), 'Location info should not appear.'

    def test_real_location_appears_in_profile_and_geocodes(self):
        """Verify a valid location appears in a user's profile/is geocoded."""
        self.client.login(email=self.mozillian.email)

        canada, created = Country.objects.get_or_create(code='ca')

        r = self.client.post(reverse('profile.edit'),
                             dict(last_name='tofumatt', city='Montreal',
                                  province='QC', country=canada.id),
                             follow=True)
        doc = pq(r.content)

        assert doc('#profile-info'), ('User should be on their profile '
                                      'page after submitting the form.')

        assert (doc('dd a.location-text'),
                'Location info should appear in the page.')

        eq_('Montreal, QC, Canada', doc('dd a.location-text').text(), (
            'Location data should appear as submitted.'))

        profile = User.objects.get(email=self.mozillian.email).get_profile()

        assert profile.address.point is not None, (
                "User's address should be geolocated and have an associated "
                'POINT object stored in the database.')

    def test_bad_location_appears_in_profile_and_doesnt_geocode(self):
        """Verify any entered location appears in a user's profile."""
        self.client.login(email=self.mozillian.email)

        r = self.client.post(reverse('profile.edit'),
                             dict(last_name='Luedecke',
                                  city='Hinterland Noplace', province='XB'),
                             follow=True)
        doc = pq(r.content)
        assert doc('#profile-info'), ('User should be on their profile '
                                      'page after submitting the form.')
        assert (doc('dd a.location-text'),
                'Location info should appear in the page.')

        eq_('Hinterland Noplace, XB', doc('dd a.location-text').text(), (
            'Location data should appear as submitted.'))

        profile = User.objects.get(email=self.mozillian.email).get_profile()
        assert (profile.address.point is None,
                "User's address should not be geolocated.")

    def test_location_can_be_removed(self):
        """Verify a user can delete their location and geo information."""
        self.client.login(email=self.mozillian.email)

        canada, created = Country.objects.get_or_create(code='ca')

        profile = User.objects.get(email=self.mozillian.email).get_profile()
        address = profile.address
        address.city = 'Halifax'
        address.province = 'NS'
        address.country = canada
        address.save()

        r = self.client.post(reverse('profile',
                             args=[self.mozillian.username]))
        doc = pq(r.content)

        assert (doc('dd a.location-text'),
                'Location info should appear in the page.')

        eq_('Halifax, NS, Canada', doc('dd a.location-text').text(),
            'Location data should appear as submitted.')

        profile = User.objects.get(email=self.mozillian.email).get_profile()
        assert (profile.address.point is not None,
                "User's address should be geolocated and have an associated "
                'POINT object stored in the database.')

        r = self.client.post(reverse('profile.edit'),
                        dict(last_name='Luedecke', city='',
                             province='', country=''),
                        follow=True)
        doc = pq(r.content)

        assert (doc('#profile-info'), 'User should be on their profile page '
                                      'after submitting the form.')

        assert (not doc('dd a.location'),
                "Location info should no longer appear on the user's profile.")

        profile = User.objects.get(email=self.mozillian.email).get_profile()
        assert (profile.address.point is None,
                "User's address should no longer be geolocated.")
