# -*- coding: utf-8 -*-
import json

from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test.utils import override_settings

from funfactory.helpers import urlparams
from funfactory.utils import absolutify
from nose.tools import eq_, ok_

from mozillians.api.tests import APIAppFactory
from mozillians.common.tests import TestCase
from mozillians.groups.tests import GroupFactory, SkillFactory
from mozillians.users.models import ExternalAccount
from mozillians.users.tests import UserFactory


class UserResourceTests(TestCase):
    def setUp(self):
        voucher = UserFactory.create()
        self.user = UserFactory.create(vouched=False)
        self.user.userprofile.vouch(voucher.userprofile)
        group = GroupFactory.create()
        group.add_member(self.user.userprofile)
        skill = SkillFactory.create()
        self.user.userprofile.skills.add(skill)
        self.user.userprofile.externalaccount_set.create(type=ExternalAccount.TYPE_SUMO,
                                                         identifier='Apitest')

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
        eq_(data['id'], profile.id)
        eq_(data['full_name'], profile.full_name)
        eq_(data['is_vouched'], profile.is_vouched)
        eq_(data['vouched_by'], profile.vouched_by.id)
        # eq_(data['date_vouched'], profile.date_vouched)
        eq_(data['groups'], list(profile.groups.values_list('name', flat=True)))
        eq_(data['skills'], list(profile.skills.values_list('name', flat=True)))
        eq_(data['accounts'],
            [{'identifier': a.identifier, 'type': a.type}
             for a in profile.externalaccount_set.all()])
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
        UserFactory.create()
        UserFactory.create()
        client = Client()
        url = urlparams(self.mozilla_resource_url, offset=1)
        response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['meta']['offset'], 1)

    def test_request_with_huge_offset(self):
        UserFactory.create()
        UserFactory.create()
        client = Client()
        url = urlparams(self.mozilla_resource_url, offset=100000000)
        response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        data = json.loads(response.content)
        eq_(data['meta']['offset'], data['meta']['total_count'])

    def test_is_vouched_true(self):
        UserFactory.create()
        UserFactory.create(vouched=False)
        client = Client()
        url = urlparams(self.mozilla_resource_url, is_vouched='true')
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        for obj in data['objects']:
            ok_(obj['is_vouched'])

    def test_is_vouched_false(self):
        UserFactory.create()
        user = UserFactory.create(vouched=False)
        client = Client()
        url = urlparams(self.mozilla_resource_url, is_vouched='false')
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], user.userprofile.id)

    def test_search_accounts(self):
        client = Client()
        user_1 = UserFactory.create()
        user_1.userprofile.externalaccount_set.create(type=ExternalAccount.TYPE_SUMO,
                                                      identifier='AccountTest')
        user_2 = UserFactory.create()
        user_2.userprofile.externalaccount_set.create(type=ExternalAccount.TYPE_SUMO,
                                                      identifier='AccountTest')

        url = urlparams(self.mozilla_resource_url, accounts='count')
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 2)
        eq_(data['objects'][0]['accounts'][0]['identifier'], 'AccountTest')

    def test_search_skills(self):
        client = Client()
        skill_1 = SkillFactory.create()
        skill_2 = SkillFactory.create()
        user_1 = UserFactory.create()
        user_1.userprofile.skills.add(skill_1)
        user_2 = UserFactory.create()
        user_2.userprofile.skills.add(skill_2)

        url = urlparams(self.mozilla_resource_url, skills=skill_1.name)
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], user_1.userprofile.id)

    def test_search_groups(self):
        client = Client()
        group_1 = GroupFactory.create()
        group_2 = GroupFactory.create()
        user_1 = UserFactory.create()
        group_1.add_member(user_1.userprofile)
        user_2 = UserFactory.create()
        group_2.add_member(user_2.userprofile)

        url = urlparams(self.mozilla_resource_url, groups=group_1.name)
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], user_1.userprofile.id)

    def test_search_combined_skills_country(self):
        country = 'fr'
        user_1 = UserFactory.create(userprofile={'country': country})
        UserFactory.create(userprofile={'country': country})
        skill = SkillFactory.create()
        user_1.userprofile.skills.add(skill)
        client = Client()
        url = urlparams(self.mozilla_resource_url,
                        skills=skill.name, country=country)
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], user_1.userprofile.id)

    def test_query_with_space(self):
        user = UserFactory.create(userprofile={'city': 'Mountain View'})
        client = Client()
        url = urlparams(self.mozilla_resource_url, city='mountain view')
        request = client.get(url, follow=True)
        data = json.loads(request.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], user.userprofile.id)

    def test_search_name(self):
        user = UserFactory.create(userprofile={'full_name': u'Νίκος Κούκος'})
        client = Client()
        url = urlparams(self.mozilla_resource_url,
                        name=user.userprofile.full_name)
        request = client.get(url, follow=True)
        data = json.loads(request.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], user.userprofile.id)

    def test_search_username(self):
        user = UserFactory.create()
        url = urlparams(self.mozilla_resource_url, username=user.username)
        client = Client()
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], user.userprofile.id)

    def test_search_country(self):
        user = UserFactory.create(userprofile={'country': 'fr'})
        url = urlparams(self.mozilla_resource_url,
                        country=user.userprofile.country)
        client = Client()
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], user.userprofile.id)

    def test_search_region(self):
        user = UserFactory.create(userprofile={'region': 'la lo'})
        url = urlparams(self.mozilla_resource_url,
                        region=user.userprofile.region)
        client = Client()
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], user.userprofile.id)

    def test_search_city(self):
        user = UserFactory.create(userprofile={'city': u'αθήνα'})
        url = urlparams(self.mozilla_resource_url,
                        city=user.userprofile.city)
        client = Client()
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], user.userprofile.id)

    def test_search_ircname(self):
        user = UserFactory.create(userprofile={'ircname': 'nikos'})
        url = urlparams(self.mozilla_resource_url,
                        ircname=user.userprofile.ircname)
        client = Client()
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['id'], user.userprofile.id)

    def test_community_app_does_not_allow_community_sites(self):
        user = UserFactory.create(userprofile={'allows_community_sites': False})
        client = Client()
        url = urlparams(self.community_resource_url, email=user.email)
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(response.status_code, 200)
        eq_(len(data['objects']), 0)

    def test_community_app_does_allows_community_sites(self):
        user = UserFactory.create(userprofile={'allows_community_sites': True})
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
        user = UserFactory.create(userprofile={'allows_mozilla_sites': False})
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
        user = UserFactory.create(userprofile={'allows_mozilla_sites': True})
        client = Client()
        url = urlparams(self.mozilla_resource_url, email=user.email)
        response = client.get(url, follow=True)
        data = json.loads(response.content)
        eq_(response.status_code, 200)
        eq_(len(data['objects']), 1)
        eq_(data['objects'][0]['email'], user.email)

    def test_only_completed_profiles(self):
        user = UserFactory.create(userprofile={'full_name': ''})
        client = Client()
        response = client.get(self.mozilla_resource_url, follow=True)
        data = json.loads(response.content)
        eq_(response.status_code, 200)
        eq_(len(data['objects']), 2)
        for obj in data['objects']:
            ok_(obj['email'] != user.email)

    def test_distinct_results(self):
        user = UserFactory.create()
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
