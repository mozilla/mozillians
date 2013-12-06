# -*- coding: utf-8 -*-
import json

from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test.utils import override_settings

from funfactory.helpers import urlparams
from funfactory.utils import absolutify
from mock import patch
from nose.tools import eq_, ok_

from mozillians.api.tests import APIAppFactory
from mozillians.common.tests import TestCase
from mozillians.groups.tests import GroupFactory, LanguageFactory, SkillFactory
from mozillians.users.api import CustomQuerySet
from mozillians.users.managers import MOZILLIANS, PUBLIC
from mozillians.users.tests import UserFactory


class CityResourceTests(TestCase):
    def setUp(self):
        self.user = UserFactory.create(userprofile={'is_vouched': True})
        self.resource_url = reverse(
            'api_dispatch_list',
            kwargs={'api_name': 'v1', 'resource_name': 'cities'})
        self.app = APIAppFactory.create(owner=self.user,
                                        is_mozilla_app=True)
        self.resource_url = urlparams(self.resource_url,
                                      app_name=self.app.name,
                                      app_key=self.app.key)

    def test_get_list(self):
        UserFactory.create(userprofile={'is_vouched': True,
                                        'country': 'gr',
                                        'city': 'Athens'})
        UserFactory.create(userprofile={'is_vouched': False,
                                        'country': 'gr',
                                        'city': 'Athens'})
        client = Client()
        response = client.get(self.resource_url, follow=True)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['meta']['total_count'], 1, 'Unvouched users get listed!')
        eq_(data['objects'][0]['city'], 'Athens')
        eq_(data['objects'][0]['country'], 'gr')
        eq_(data['objects'][0]['country_name'], 'Greece')
        eq_(data['objects'][0]['population'], 1)
        eq_(data['objects'][0]['url'],
            absolutify(reverse('phonebook:list_city', args=['gr', 'Athens'])))

    def test_not_duplicated(self):
        # Ensure if there are users from the same city with different
        # privacy settings, the city API only returns that city once.
        # Also, the population should be the total.
        # Note that setUp() already created one User, but that User has
        # no city and so should not show up in these results.
        UserFactory.create(userprofile={'is_vouched': True,
                                        'privacy_city': MOZILLIANS,
                                        'city': 'Athens'})
        UserFactory.create(userprofile={'is_vouched': True,
                                        'privacy_city': PUBLIC,
                                        'city': 'Athens'})
        client = Client()
        response = client.get(self.resource_url, follow=True)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['meta']['total_count'], 1)
        eq_(data['objects'][0]['population'], 2)
        eq_(data['objects'][0]['city'], 'Athens')

    def test_get_details(self):
        client = Client()
        url = reverse('api_dispatch_detail',
                      kwargs={'api_name': 'v1',
                              'resource_name': 'cities', 'pk': 1})
        response = client.get(url, follow=True)
        eq_(response.status_code, 405)

    @patch('mozillians.users.api.CustomQuerySet.order_by',
           wraps=CustomQuerySet.order_by)
    def test_default_ordering(self, order_by_mock):
        client = Client()
        client.get(self.resource_url, follow=True)
        order_by_mock.assert_called_with('country', 'city')

    @patch('mozillians.users.api.CustomQuerySet.order_by',
           wraps=CustomQuerySet.order_by)
    def test_custom_ordering(self, order_by_mock):
        client = Client()
        url = urlparams(self.resource_url, order_by='-population')
        client.get(url, follow=True)
        order_by_mock.assert_called_with('-population')

    @patch('mozillians.users.api.CustomQuerySet.order_by',
           wraps=CustomQuerySet.order_by)
    def test_custom_invalid_ordering(self, order_by_mock):
        client = Client()
        url = urlparams(self.resource_url, order_by='foo')
        client.get(url, follow=True)
        order_by_mock.assert_called_with('country', 'city')

    @patch('mozillians.users.api.CustomQuerySet.filter',
           wraps=CustomQuerySet.filter)
    def test_filtering(self, filter_mock):
        url = urlparams(self.resource_url, city='athens')
        client = Client()
        client.get(url, follow=True)
        ok_(filter_mock.called)
        call_arg = filter_mock.call_args[0][0]
        eq_(call_arg.children, [('city__iexact', 'athens')])

    @patch('mozillians.users.api.CustomQuerySet.filter',
           wraps=CustomQuerySet.filter)
    def test_invalid_filtering(self, filter_mock):
        url = urlparams(self.resource_url, foo='bar')
        client = Client()
        client.get(url, follow=True)
        ok_(not filter_mock.called)


class CountryResourceTests(TestCase):
    def setUp(self):
        self.user = UserFactory.create(userprofile={'is_vouched': True})
        self.resource_url = reverse(
            'api_dispatch_list',
            kwargs={'api_name': 'v1', 'resource_name': 'countries'})
        self.app = APIAppFactory.create(owner=self.user,
                                        is_mozilla_app=True)
        self.resource_url = urlparams(self.resource_url,
                                      app_name=self.app.name,
                                      app_key=self.app.key)

    def test_get_list(self):
        UserFactory.create(userprofile={'is_vouched': False, 'country': 'gr'})
        client = Client()
        response = client.get(self.resource_url, follow=True)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['meta']['total_count'], 1, 'Unvouched users get listed!')
        eq_(data['objects'][0]['country'], 'gr')
        eq_(data['objects'][0]['country_name'], 'Greece')
        eq_(data['objects'][0]['population'], 1)
        eq_(data['objects'][0]['url'],
            absolutify(reverse('phonebook:list_country', args=['gr'])))

    def test_not_duplicated(self):
        # If mozillians from the same country have different privacy_country
        # settings, make sure we don't return the country twice in the API
        # result.
        # Also, the population should be the total.

        # NOTE: There's already one Greek created in setUp()

        # Create a couple more Greeks with each privacy setting.  We should
        # still get back Greece only once.
        for i in xrange(2):
            UserFactory.create(userprofile={'is_vouched': True,
                                            'country': 'gr',
                                            'privacy_country': MOZILLIANS})
        for i in xrange(2):
            UserFactory.create(userprofile={'is_vouched': True,
                                            'country': 'gr',
                                            'privacy_country': PUBLIC})

        # One person from another country, to make sure that country shows up too.
        UserFactory.create(userprofile={'is_vouched': True,
                                        'country': 'us',
                                        'privacy_country': MOZILLIANS})

        client = Client()
        response = client.get(self.resource_url, follow=True)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        # We should get back Gr and Us
        eq_(data['meta']['total_count'], 2)
        for obj in data['objects']:
            if obj['country'] == 'gr':
                # 5 greeks
                eq_(obj['population'], 5)
            else:
                # 1 USian
                eq_(obj['population'], 1)

    def test_get_details(self):
        client = Client()
        url = reverse('api_dispatch_detail',
                      kwargs={'api_name': 'v1',
                              'resource_name': 'countries', 'pk': 1})
        response = client.get(url, follow=True)
        eq_(response.status_code, 405)

    @patch('mozillians.users.api.CustomQuerySet.order_by',
           wraps=CustomQuerySet.order_by)
    def test_default_ordering(self, order_by_mock):
        client = Client()
        client.get(self.resource_url, follow=True)
        order_by_mock.assert_called_with('country')

    @patch('mozillians.users.api.CustomQuerySet.order_by',
           wraps=CustomQuerySet.order_by)
    def test_custom_ordering(self, order_by_mock):
        client = Client()
        url = urlparams(self.resource_url, order_by='-population')
        client.get(url, follow=True)
        order_by_mock.assert_called_with('-population')

    @patch('mozillians.users.api.CustomQuerySet.order_by',
           wraps=CustomQuerySet.order_by)
    def test_custom_invalid_ordering(self, order_by_mock):
        client = Client()
        url = urlparams(self.resource_url, order_by='foo')
        client.get(url, follow=True)
        order_by_mock.assert_called_with('country')

    @patch('mozillians.users.api.CustomQuerySet.filter',
           wraps=CustomQuerySet.filter)
    def test_filtering(self, filter_mock):
        url = urlparams(self.resource_url, country='gr')
        client = Client()
        client.get(url, follow=True)
        ok_(not filter_mock.called)


class UserResourceTests(TestCase):
    def setUp(self):
        voucher = UserFactory.create(userprofile={'is_vouched': True})
        self.user = UserFactory.create(
            userprofile={'is_vouched': True,
                         'vouched_by': voucher.userprofile})
        group = GroupFactory.create()
        group.add_member(self.user.userprofile)
        skill = SkillFactory.create()
        self.user.userprofile.skills.add(skill)
        language = LanguageFactory.create()
        self.user.userprofile.languages.add(language)

        self.resource_url = reverse(
            'api_dispatch_list',
            kwargs={'api_name': 'v1', 'resource_name': 'users'})
        self.mozilla_app = APIAppFactory.create(
            owner=self.user, is_mozilla_app=True)
        self.mozilla_resource_url = urlparams(
            self.resource_url, app_name=self.mozilla_app.name,
            app_key=self.mozilla_app.key)
        self.community_app = APIAppFactory.create(
            owner=self.user, is_mozilla_app=False)
        self.community_resource_url = urlparams(
            self.resource_url, app_name=self.community_app.name,
            app_key=self.community_app.key)

    def test_get_list_mozilla_app(self):
        client = Client()
        response = client.get(self.mozilla_resource_url, follow=True)
        eq_(response.status_code, 200)
        ok_(json.loads(response.content))

    def test_get_list_community_app(self):
        client = Client()
        response = client.get(self.community_resource_url, follow=True)
        eq_(response.status_code, 403)

    def test_get_detail_mozilla_app(self):
        client = Client()
        url = reverse('api_dispatch_detail',
                      kwargs={'api_name': 'v1', 'resource_name': 'users',
                              'pk': self.user.userprofile.id})
        url = urlparams(url, app_name=self.mozilla_app.name,
                        app_key=self.mozilla_app.key)
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        profile = self.user.userprofile
        eq_(response.status_code, 200)
        eq_(data['id'], unicode(profile.id))
        eq_(data['full_name'], profile.full_name)
        eq_(data['is_vouched'], profile.is_vouched)
        eq_(data['vouched_by'], profile.vouched_by.user.id)
        eq_(data['date_vouched'], profile.date_vouched)
        eq_(data['groups'], list(profile.groups.values_list('name', flat=True)))
        eq_(data['skills'], list(profile.skills.values_list('name', flat=True)))
        eq_(data['languages'], list(profile.languages.values_list('name', flat=True)))
        eq_(data['bio'], profile.bio)
        eq_(data['photo'], profile.photo)
        eq_(data['ircname'], profile.ircname)
        eq_(data['country'], profile.country)
        eq_(data['region'], profile.region)
        eq_(data['city'], profile.city)
        eq_(data['date_mozillian'], profile.date_mozillian)
        eq_(data['timezone'], profile.timezone)
        eq_(data['email'], profile.email)
        eq_(data['url'],
            absolutify(reverse('phonebook:profile_view',
                               args=[profile.user.username])))

    def test_get_detail_community_app(self):
        client = Client()
        url = reverse('api_dispatch_detail',
                      kwargs={'api_name': 'v1', 'resource_name': 'users',
                              'pk': self.user.userprofile.id})
        url = urlparams(url, app_name=self.community_app.name,
                        app_key=self.community_app.key)
        response = client.get(url, follow=True)
        eq_(response.status_code, 403)

    @override_settings(HARD_API_LIMIT_PER_PAGE=10)
    def test_request_with_normal_limit(self):
        client = Client()
        url = urlparams(self.mozilla_resource_url, limit=5)
        response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['meta']['limit'], 5)

    @override_settings(HARD_API_LIMIT_PER_PAGE=1)
    def test_request_with_huge_limit(self):
        client = Client()
        url = urlparams(self.mozilla_resource_url, limit=200000000000000000000)
        response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['meta']['limit'], 1)

    def test_request_with_normal_offset(self):
        UserFactory.create(userprofile={'is_vouched': True})
        UserFactory.create(userprofile={'is_vouched': True})
        client = Client()
        url = urlparams(self.mozilla_resource_url, offset=1)
        response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['meta']['offset'], 1)

    def test_request_with_huge_offset(self):
        UserFactory.create(userprofile={'is_vouched': True})
        UserFactory.create(userprofile={'is_vouched': True})
        client = Client()
        url = urlparams(self.mozilla_resource_url, offset=100000000)
        response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['meta']['offset'], data['meta']['total_count'])

    def test_is_vouched_true(self):
        UserFactory.create(userprofile={'is_vouched': True})
        UserFactory.create(userprofile={'is_vouched': False})
        client = Client()
        url = urlparams(self.mozilla_resource_url, is_vouched='true')
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        for obj in data['objects']:
            ok_(obj['is_vouched'])

    def test_is_vouched_false(self):
        UserFactory.create(userprofile={'is_vouched': True})
        user = UserFactory.create(userprofile={'is_vouched': False})
        client = Client()
        url = urlparams(self.mozilla_resource_url, is_vouched='false')
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], unicode(user.userprofile.id))

    def test_search_languages(self):
        client = Client()
        language_1 = LanguageFactory.create()
        language_2 = LanguageFactory.create()
        user_1 = UserFactory.create(userprofile={'is_vouched': True})
        user_1.userprofile.languages.add(language_1)
        user_2 = UserFactory.create(userprofile={'is_vouched': True})
        user_2.userprofile.languages.add(language_2)

        url = urlparams(self.mozilla_resource_url, languages=language_1.name)
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], unicode(user_1.userprofile.id))

    def test_search_multiple_languages(self):
        client = Client()
        language_1 = LanguageFactory.create()
        language_2 = LanguageFactory.create()
        user_1 = UserFactory.create(userprofile={'is_vouched': True})
        user_1.userprofile.languages.add(language_1)
        user_2 = UserFactory.create(userprofile={'is_vouched': True})
        user_2.userprofile.languages.add(language_2)

        url = urlparams(self.mozilla_resource_url,
                        languages=','.join([language_1.name, language_2.name]))
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 2)
        eq_(data['objects'][0]['id'], unicode(user_1.userprofile.id))
        eq_(data['objects'][1]['id'], unicode(user_2.userprofile.id))

    def test_search_skills(self):
        client = Client()
        skill_1 = SkillFactory.create()
        skill_2 = SkillFactory.create()
        user_1 = UserFactory.create(userprofile={'is_vouched': True})
        user_1.userprofile.skills.add(skill_1)
        user_2 = UserFactory.create(userprofile={'is_vouched': True})
        user_2.userprofile.skills.add(skill_2)

        url = urlparams(self.mozilla_resource_url, skills=skill_1.name)
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], unicode(user_1.userprofile.id))

    def test_search_groups(self):
        client = Client()
        group_1 = GroupFactory.create()
        group_2 = GroupFactory.create()
        user_1 = UserFactory.create(userprofile={'is_vouched': True})
        group_1.add_member(user_1.userprofile)
        user_2 = UserFactory.create(userprofile={'is_vouched': True})
        group_2.add_member(user_2.userprofile)

        url = urlparams(self.mozilla_resource_url, groups=group_1.name)
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], unicode(user_1.userprofile.id))

    def test_search_combined_skills_country(self):
        country = 'fr'
        user_1 = UserFactory.create(userprofile={'is_vouched': True,
                                                 'country': country})
        UserFactory.create(userprofile={'is_vouched': True, 'country': country})
        skill = SkillFactory.create()
        user_1.userprofile.skills.add(skill)
        client = Client()
        url = urlparams(self.mozilla_resource_url,
                        skills=skill.name, country=country)
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], unicode(user_1.userprofile.id))

    def test_query_with_space(self):
        user = UserFactory.create(userprofile={'is_vouched': True,
                                               'city': 'Mountain View'})
        client = Client()
        url = urlparams(self.mozilla_resource_url, city='mountain view')
        request = client.get(url, follow=True)
        data = json.loads(request.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], unicode(user.userprofile.id))

    def test_search_name(self):
        user = UserFactory.create(userprofile={'is_vouched': True,
                                               'full_name': u'Νίκος Κούκος'})
        client = Client()
        url = urlparams(self.mozilla_resource_url,
                        name=user.userprofile.full_name)
        request = client.get(url, follow=True)
        data = json.loads(request.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], unicode(user.userprofile.id))

    def test_search_username(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = urlparams(self.mozilla_resource_url, username=user.username)
        client = Client()
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], unicode(user.userprofile.id))

    def test_search_country(self):
        user = UserFactory.create(userprofile={'is_vouched': True,
                                               'country': 'fr'})
        url = urlparams(self.mozilla_resource_url,
                        country=user.userprofile.country)
        client = Client()
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], unicode(user.userprofile.id))

    def test_search_region(self):
        user = UserFactory.create(userprofile={'is_vouched': True,
                                               'region': 'la lo'})
        url = urlparams(self.mozilla_resource_url,
                        region=user.userprofile.region)
        client = Client()
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], unicode(user.userprofile.id))

    def test_search_city(self):
        user = UserFactory.create(userprofile={'is_vouched': True,
                                               'city': u'αθήνα'})
        url = urlparams(self.mozilla_resource_url,
                        city=user.userprofile.city)
        client = Client()
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], unicode(user.userprofile.id))

    def test_search_ircname(self):
        user = UserFactory.create(userprofile={'is_vouched': True,
                                               'ircname': 'nikos'})
        url = urlparams(self.mozilla_resource_url,
                        ircname=user.userprofile.ircname)
        client = Client()
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], unicode(user.userprofile.id))

    def test_community_app_does_not_allow_community_sites(self):
        user = UserFactory.create(
            userprofile={'is_vouched': True, 'allows_community_sites': False})
        client = Client()
        url = urlparams(self.community_resource_url, email=user.email)
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(response.status_code, 200)
        eq_(len(data['objects']), 0)

    def test_community_app_does_allows_community_sites(self):
        user = UserFactory.create(userprofile={'is_vouched': True,
                                               'allows_community_sites': True})
        client = Client()
        url = urlparams(self.community_resource_url, email=user.email)
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(response.status_code, 200)
        eq_(len(data['objects']), 1)
        eq_(len(data['objects'][0]), 2)
        eq_(data['objects'][0]['email'], user.email)
        eq_(data['objects'][0]['is_vouched'], user.userprofile.is_vouched)

    def test_mozillian_app_does_not_allow_mozilla_sites(self):
        user = UserFactory.create(
            userprofile={'is_vouched': True, 'allows_mozilla_sites': False})
        client = Client()
        url = urlparams(self.mozilla_resource_url, email=user.email)
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(response.status_code, 200)
        eq_(len(data['objects']), 1)
        eq_(len(data['objects'][0]), 2)
        eq_(data['objects'][0]['email'], user.email)
        eq_(data['objects'][0]['is_vouched'], user.userprofile.is_vouched)

    def test_mozilla_app_does_allows_mozilla_sites(self):
        user = UserFactory.create(
            userprofile={'is_vouched': True, 'allows_mozilla_sites': True})
        client = Client()
        url = urlparams(self.mozilla_resource_url, email=user.email)
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(response.status_code, 200)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['email'], user.email)

    def test_only_completed_profiles(self):
        user = UserFactory.create(userprofile={'is_vouched': True, 'full_name': ''})
        client = Client()
        response = client.get(self.mozilla_resource_url, follow=True)
        data = json.loads(response.content)
        eq_(response.status_code, 200)
        eq_(len(data['objects']), 2)
        for obj in data['objects']:
            ok_(obj['email'] != user.email)

    def test_distinct_results(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        group_1 = GroupFactory.create()
        group_2 = GroupFactory.create()
        group_1.add_member(user.userprofile)
        group_2.add_member(user.userprofile)
        client = Client()
        url = urlparams(self.mozilla_resource_url,
                        groups=','.join([group_1.name, group_2.name]))
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(response.status_code, 200)
        eq_(len(data['objects']), 1)
