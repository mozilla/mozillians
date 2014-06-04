# -*- coding: utf-8 -*-
from django.http import Http404

from mock import Mock, patch
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.geo.tests import CityFactory, CountryFactory, RegionFactory
from mozillians.users.managers import MOZILLIANS, PUBLIC
from mozillians.users.models import ExternalAccount, Language
from mozillians.users.tests import UserFactory
from mozillians.users.api.v2 import (ExternalAccountSerializer,
                                     LanguageSerializer,
                                     UserProfileDetailedSerializer,
                                     UserProfileSerializer,
                                     UserProfileViewSet,
                                     WebsiteSerializer)


class ExternalAccountSerializerTests(TestCase):
    def test_base(self):
        account = ExternalAccount(identifier='foobar',
                                  type=ExternalAccount.TYPE_AMO, privacy=PUBLIC)
        serializer = ExternalAccountSerializer(account)
        data = serializer.data
        eq_(data, {'type': 'amo',
                   'identifier': 'foobar',
                   'name': 'Mozilla Add-ons',
                   'privacy': 'Public'})


class WebsiteSerializerTests(TestCase):
    def test_base(self):
        account = ExternalAccount(identifier='http://example.com',
                                  type=ExternalAccount.TYPE_WEBSITE, privacy=PUBLIC)
        serializer = WebsiteSerializer(account)
        data = serializer.data
        eq_(data, {'value': 'http://example.com',
                   'privacy': 'Public'})


class LanguageSerializerTests(TestCase):
    def test_base(self):
        language = Language(code='el')
        serializer = LanguageSerializer(language)
        data = serializer.data
        eq_(data, {'code': 'el',
                   'english': 'Greek',
                   'native': u'Ελληνικά'})


class UserProfileSerializerTests(TestCase):
    def test_base(self):
        user = UserFactory.create(username='foo')
        profile = user.userprofile

        serializer = UserProfileSerializer(profile)
        data = serializer.data
        eq_(data['username'], 'foo')
        eq_(data['is_vouched'], True)
        ok_(data['_url'])


class UserProfileDetailedSerializerTests(TestCase):
    def test_transform_timezone(self):
        user = UserFactory.create(userprofile={'timezone': 'Europe/Athens'})
        timezone_mock = Mock()
        timezone_mock.return_value = 99
        user.userprofile.timezone_offset = timezone_mock
        data = UserProfileDetailedSerializer(user.userprofile).data
        timezone = {'value': 'Europe/Athens',
                    'utc_offset': 99,
                    'privacy': 'Mozillians'}
        eq_(data['timezone'], timezone)

    def test_transform_bio(self):
        user = UserFactory.create(userprofile={'bio': '*foo*'})
        data = UserProfileDetailedSerializer(user.userprofile).data
        bio = {'value': '*foo*',
               'html': '<p><em>foo</em></p>',
               'privacy': 'Mozillians'}
        eq_(data['bio'], bio)

    def test_transform_photo(self):
        def _get_url(dimensions):
            return dimensions

        user = UserFactory.create(userprofile={'timezone': 'Europe/Athens'})
        get_photo_url_mock = Mock()
        get_photo_url_mock.side_effect = _get_url
        user.userprofile.get_photo_url = get_photo_url_mock
        data = UserProfileDetailedSerializer(user.userprofile).data
        photo = {'value': '300x300',
                 '150x150': '150x150',
                 '300x300': '300x300',
                 '500x500': '500x500',
                 'privacy': 'Mozillians'}
        eq_(data['photo'], photo)

    def test_transform_country(self):
        country = CountryFactory.create(name='LA', code='IO')
        user = UserFactory.create(userprofile={'geo_country': country})
        data = UserProfileDetailedSerializer(user.userprofile).data
        country = {'code': 'IO',
                   'value': 'LA',
                   'privacy': 'Mozillians'}
        eq_(data['country'], country)

    def test_transform_region(self):
        region = RegionFactory.create(name='LA')
        user = UserFactory.create(userprofile={'geo_region': region})
        data = UserProfileDetailedSerializer(user.userprofile).data
        region = {'value': 'LA',
                  'privacy': 'Mozillians'}
        eq_(data['region'], region)

    def test_transform_city(self):
        city = CityFactory.create(name='LA')
        user = UserFactory.create(userprofile={'geo_city': city})
        data = UserProfileDetailedSerializer(user.userprofile).data
        city = {'value': 'LA',
                'privacy': 'Mozillians'}
        eq_(data['city'], city)

    def test_transform_tshirt(self):
        user = UserFactory.create(userprofile={'tshirt': 9})
        data = UserProfileDetailedSerializer(user.userprofile).data
        tshirt = {'value': 9,
                  'english': 'Straight-cut Large',
                  'privacy': 'Privileged'}
        eq_(data['tshirt'], tshirt)


class UserProfileViewSetTests(TestCase):
    def test_get_queryset_public(self):
        viewset = UserProfileViewSet()
        viewset.request = Mock()
        viewset.request.privacy_level = PUBLIC
        with patch('mozillians.users.api.v2.UserProfile') as userprofile_mock:
            viewset.get_queryset()

        ok_(userprofile_mock.objects.complete.called)
        ok_(userprofile_mock.objects.complete().public.called)
        userprofile_mock.objects.complete().public().privacy_level.assert_called_with(PUBLIC)

    def test_get_queryset_non_public(self):
        viewset = UserProfileViewSet()
        viewset.request = Mock()
        viewset.request.privacy_level = MOZILLIANS
        with patch('mozillians.users.api.v2.UserProfile') as userprofile_mock:
            viewset.get_queryset()

        ok_(userprofile_mock.objects.complete.called)
        userprofile_mock.objects.complete().privacy_level.assert_called_with(MOZILLIANS)

    def test_retrieve_base(self):
        viewset = UserProfileViewSet()
        viewset.request = Mock()
        viewset.request.privacy_level = MOZILLIANS
        user = UserFactory.create()
        with patch('mozillians.users.api.v2.UserProfileDetailedSerializer') as serializer_mock:
            viewset.retrieve(None, user.userprofile.id)

        serializer_mock.assert_called_with(user.userprofile)

    def test_retrieve_non_existent(self):
        viewset = UserProfileViewSet()
        viewset.request = Mock()
        viewset.request.privacy_level = MOZILLIANS
        self.assertRaises(Http404, viewset.retrieve, viewset.request, -1)
