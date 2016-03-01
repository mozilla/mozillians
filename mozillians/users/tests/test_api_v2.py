# -*- coding: utf-8 -*-
from django.http import Http404
from django.test import RequestFactory

from mock import ANY, Mock, patch
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.geo.tests import CityFactory, CountryFactory, RegionFactory
from mozillians.groups.tests import GroupFactory
from mozillians.users.managers import MOZILLIANS, PUBLIC
from mozillians.users.models import GroupMembership, ExternalAccount, Language, UserProfile
from mozillians.users.tests import UserFactory
from mozillians.users.api.v2 import (ExternalAccountSerializer,
                                     LanguageSerializer,
                                     UserProfileDetailedSerializer,
                                     UserProfileFilter,
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
        eq_(data, {'website': 'http://example.com',
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
    def setUp(self):
        self.factory = RequestFactory()

    def test_base(self):
        user = UserFactory.create(username='foo')
        profile = user.userprofile
        context = {'request': self.factory.get('/')}
        serializer = UserProfileSerializer(profile, context=context)
        data = serializer.data
        eq_(data['username'], 'foo')
        eq_(data['is_vouched'], True)
        ok_(data['_url'])


class UserProfileDetailedSerializerTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_transform_timezone(self):
        user = UserFactory.create(userprofile={'timezone': 'Europe/Athens'})
        timezone_mock = Mock()
        timezone_mock.return_value = 99
        user.userprofile.timezone_offset = timezone_mock
        context = {'request': self.factory.get('/')}
        serializer = UserProfileDetailedSerializer(user.userprofile, context=context)
        timezone = {'value': 'Europe/Athens',
                    'utc_offset': 99,
                    'privacy': 'Mozillians'}
        eq_(serializer.data['timezone'], timezone)

    def test_transform_bio(self):
        user = UserFactory.create(userprofile={'bio': '*foo*'})
        context = {'request': self.factory.get('/')}
        serializer = UserProfileDetailedSerializer(user.userprofile, context=context)
        bio = {'value': '*foo*',
               'html': '<p><em>foo</em></p>',
               'privacy': 'Mozillians'}
        eq_(serializer.data['bio'], bio)

    def test_transform_photo(self):
        def _get_url(dimensions):
            return dimensions

        user = UserFactory.create(userprofile={'timezone': 'Europe/Athens'})
        context = {'request': self.factory.get('/')}
        get_photo_url_mock = Mock()
        get_photo_url_mock.side_effect = _get_url
        user.userprofile.get_photo_url = get_photo_url_mock
        serializer = UserProfileDetailedSerializer(user.userprofile, context=context)
        photo = {'value': '300x300',
                 '150x150': '150x150',
                 '300x300': '300x300',
                 '500x500': '500x500',
                 'privacy': 'Mozillians'}
        eq_(serializer.data['photo'], photo)

    def test_get_country(self):
        context = {'request': self.factory.get('/')}
        country = CountryFactory.create(name='LA', code='IO')
        user = UserFactory.create(userprofile={'geo_country': country})
        serializer = UserProfileDetailedSerializer(user.userprofile, context=context)
        country = {'code': 'IO',
                   'value': 'LA',
                   'privacy': 'Mozillians'}
        eq_(serializer.data['country'], country)

    def test_transform_region(self):
        region = RegionFactory.create(name='LA')
        user = UserFactory.create(userprofile={'geo_region': region})
        context = {'request': self.factory.get('/')}
        serializer = UserProfileDetailedSerializer(user.userprofile, context=context)
        region = {'value': 'LA',
                  'privacy': 'Mozillians'}
        eq_(serializer.data['region'], region)

    def test_transform_city(self):
        city = CityFactory.create(name='LA')
        user = UserFactory.create(userprofile={'geo_city': city})
        context = {'request': self.factory.get('/')}
        serializer = UserProfileDetailedSerializer(user.userprofile, context=context)
        city = {'value': 'LA',
                'privacy': 'Mozillians'}
        eq_(serializer.data['city'], city)

    def test_transform_tshirt(self):
        user = UserFactory.create(userprofile={'tshirt': 9})
        context = {'request': self.factory.get('/')}
        serializer = UserProfileDetailedSerializer(user.userprofile, context=context)
        tshirt = {'value': 9,
                  'english': 'Straight-cut Large',
                  'privacy': 'Privileged'}
        eq_(serializer.data['tshirt'], tshirt)


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

        serializer_mock.assert_called_with(user.userprofile, context=ANY)

    def test_retrieve_non_existent(self):
        viewset = UserProfileViewSet()
        viewset.request = Mock()
        viewset.request.privacy_level = MOZILLIANS
        self.assertRaises(Http404, viewset.retrieve, viewset.request, -1)


class UserProfileFilterTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_filter_emails_primary(self):
        request = self.factory.get('/', {'email': 'foo@bar.com'})
        user = UserFactory.create(email='foo@bar.com')
        UserFactory.create_batch(2)
        ExternalAccount.objects.create(user=user.userprofile, type=ExternalAccount.TYPE_EMAIL,
                                       identifier='bar@bar.com')
        f = UserProfileFilter(request.GET, queryset=UserProfile.objects.all())
        eq_(f.qs.count(), 1)
        eq_(f.qs[0], user.userprofile)

    def test_filter_emails_alternate(self):
        request = self.factory.get('/', {'email': 'bar@bar.com'})
        user = UserFactory.create(email='foo@bar.com')
        UserFactory.create_batch(2)
        ExternalAccount.objects.create(user=user.userprofile, type=ExternalAccount.TYPE_EMAIL,
                                       identifier='bar@bar.com')
        f = UserProfileFilter(request.GET, queryset=UserProfile.objects.all())
        eq_(f.qs.count(), 1)
        eq_(f.qs[0], user.userprofile)

    def test_filter_group_member(self):
        request = self.factory.get('/', {'group': 'bar'})
        user = UserFactory.create()
        group = GroupFactory.create(name='bar')
        group.add_member(user.userprofile)

        f = UserProfileFilter(request.GET, queryset=UserProfile.objects.all())
        eq_(f.qs.count(), 1)
        eq_(f.qs[0], user.userprofile)

    def test_filter_group_pending(self):
        request = self.factory.get('/', {'group': 'bar'})
        user = UserFactory.create()
        group = GroupFactory.create(name='bar')
        group.add_member(user.userprofile, GroupMembership.PENDING)

        f = UserProfileFilter(request.GET, queryset=UserProfile.objects.all())
        eq_(f.qs.count(), 0)
