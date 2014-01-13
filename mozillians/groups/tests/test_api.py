import json

from django.core.urlresolvers import reverse
from django.test.client import Client

from funfactory.helpers import urlparams
from funfactory.utils import absolutify
from nose.tools import eq_

from mozillians.api.tests import APIAppFactory
from mozillians.common.tests import TestCase
from mozillians.groups.models import Group
from mozillians.groups.tests import LanguageFactory, SkillFactory
from mozillians.users.tests import UserFactory


class GroupResourceTests(TestCase):
    def setUp(self):
        self.resource_url = reverse(
            'api_dispatch_list',
            kwargs={'api_name': 'v1', 'resource_name': 'groups'})
        self.user = UserFactory.create(userprofile={'is_vouched': True})
        self.app = APIAppFactory.create(owner=self.user,
                                        is_mozilla_app=True)
        self.resource_url = urlparams(self.resource_url,
                                      app_name=self.app.name,
                                      app_key=self.app.key)

    def test_list_groups(self):
        unvouched_user = UserFactory.create()
        user = UserFactory.create(userprofile={'is_vouched': True})
        group = Group.objects.get(name='staff')
        group.add_member(unvouched_user.userprofile)
        group.add_member(user.userprofile)

        client = Client()
        response = client.get(self.resource_url, follow=True)
        data = json.loads(response.content)
        eq_(data['meta']['total_count'], 1)
        eq_(data['objects'][0]['name'], group.name)

        eq_(data['objects'][0]['number_of_members'], 1,
            'List includes unvouched users')
        eq_(int(data['objects'][0]['id']), group.id)
        eq_(data['objects'][0]['url'],
            absolutify(reverse('groups:show_group', args=[group.url])))


class SkillResourceTests(TestCase):
    def setUp(self):
        self.resource_url = reverse(
            'api_dispatch_list',
            kwargs={'api_name': 'v1', 'resource_name': 'skills'})
        self.user = UserFactory.create(userprofile={'is_vouched': True})
        self.app = APIAppFactory.create(owner=self.user,
                                        is_mozilla_app=True)
        self.resource_url = urlparams(self.resource_url,
                                      app_name=self.app.name,
                                      app_key=self.app.key)

    def test_list_skills(self):
        unvouched_user = UserFactory.create()
        user = UserFactory.create(userprofile={'is_vouched': True})
        skill = SkillFactory.create()
        skill.members.add(unvouched_user.userprofile)
        skill.members.add(user.userprofile)

        client = Client()
        response = client.get(self.resource_url, follow=True)
        data = json.loads(response.content)
        eq_(data['meta']['total_count'], 1)
        eq_(data['objects'][0]['name'], skill.name)
        eq_(data['objects'][0]['number_of_members'], 1,
            'List includes unvouched users')
        eq_(int(data['objects'][0]['id']), skill.id)


class LanguageResourceTests(TestCase):
    def setUp(self):
        self.resource_url = reverse(
            'api_dispatch_list',
            kwargs={'api_name': 'v1', 'resource_name': 'languages'})
        self.user = UserFactory.create(userprofile={'is_vouched': True})
        self.app = APIAppFactory.create(owner=self.user,
                                        is_mozilla_app=True)
        self.resource_url = urlparams(self.resource_url,
                                      app_name=self.app.name,
                                      app_key=self.app.key)

    def test_list_languages(self):
        unvouched_user = UserFactory.create()
        user = UserFactory.create(userprofile={'is_vouched': True})
        language = LanguageFactory.create()
        language.members.add(unvouched_user.userprofile)
        language.members.add(user.userprofile)

        client = Client()
        response = client.get(self.resource_url, follow=True)
        data = json.loads(response.content)
        eq_(data['meta']['total_count'], 1)
        eq_(data['objects'][0]['name'], language.name)
        eq_(data['objects'][0]['number_of_members'], 1,
            'List includes unvouched users')
        eq_(int(data['objects'][0]['id']), language.id)
