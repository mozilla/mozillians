import json

from django.core.urlresolvers import reverse
from django.http import HttpResponseBadRequest
from django.test import Client

from funfactory.helpers import urlparams
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase, requires_login, requires_vouch
from mozillians.groups.tests import GroupFactory, SkillFactory
from mozillians.users.tests import UserFactory


class IndexTests(TestCase):
    def setUp(self):
        self.url = reverse('groups:index_groups')

    def test_index(self):
        user_1 = UserFactory.create()
        user_2 = UserFactory.create()
        group_1 = GroupFactory.create()
        group_2 = GroupFactory.create()
        group_1.add_member(user_1.userprofile)
        group_1.add_member(user_2.userprofile)
        group_2.add_member(user_1.userprofile)

        with self.login(user_1) as client:
            response = client.get(self.url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'groups/index_groups.html')
        eq_(set(response.context['groups'].paginator.object_list), set([group_1, group_2]))

        # Member counts
        group1 = response.context['groups'].paginator.object_list.get(pk=group_1.pk)
        eq_(group1.member_count, 2)

    @requires_login()
    def test_index_anonymous(self):
        client = Client()
        client.get(self.url, follow=True)

    @requires_vouch()
    def test_index_unvouched(self):
        user = UserFactory.create(vouched=False)
        with self.login(user) as client:
            client.get(self.url, follow=True)


class IndexFunctionalAreasTests(TestCase):
    def setUp(self):
        self.url = reverse('groups:index_functional_areas')

    def test_index_functional_areas(self):
        user = UserFactory.create()
        group_1 = GroupFactory.create(functional_area=True)
        group_1.curators.add(user.userprofile)
        group_2 = GroupFactory.create()
        GroupFactory.create()
        group_1.add_member(user.userprofile)
        group_2.add_member(user.userprofile)

        with self.login(user) as client:
            response = client.get(self.url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'groups/index_areas.html')
        eq_(set(response.context['groups'].paginator.object_list),
            set([group_1]))

    @requires_login()
    def test_index_functional_areas_anonymous(self):
        client = Client()
        client.get(self.url, follow=True)

    @requires_vouch()
    def test_index_functional_areas_unvouched(self):
        user = UserFactory.create(vouched=False)
        with self.login(user) as client:
            client.get(self.url, follow=True)


class IndexSkillsTests(TestCase):
    def setUp(self):
        self.url = reverse('groups:index_skills')

    def test_index_skills(self):
        user = UserFactory.create()
        skill_1 = SkillFactory.create()
        skill_2 = SkillFactory.create()
        SkillFactory.create()
        skill_1.members.add(user.userprofile)
        skill_2.members.add(user.userprofile)

        with self.login(user) as client:
            response = client.get(self.url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'groups/index_skills.html')
        eq_(set(response.context['groups'].paginator.object_list),
            set([skill_1, skill_2]))

    @requires_login()
    def test_index_skills_anonymous(self):
        client = Client()
        client.get(self.url, follow=True)

    @requires_vouch()
    def test_index_skills_unvouched(self):
        user = UserFactory.create(vouched=False)
        with self.login(user) as client:
            client.get(self.url, follow=True)


class SearchTests(TestCase):
    def test_search_existing_group(self):
        user = UserFactory.create()
        group_1 = GroupFactory.create(visible=True)
        GroupFactory.create()
        url = urlparams(reverse('groups:search_groups'), term=group_1.name)
        with self.login(user) as client:
            response = client.get(url, follow=True,
                                  **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})
        eq_(response.status_code, 200)
        eq_(response.get('content-type'), 'application/json')

        data = json.loads(response.content)
        eq_(len(data), 1, 'Non autocomplete groups are included in search')
        eq_(data[0], group_1.name)

    def test_search_invalid_group(self):
        user = UserFactory.create()
        url = urlparams(reverse('groups:search_groups'), term='invalid')
        with self.login(user) as client:
            response = client.get(url, follow=True,
                                  **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})
        eq_(response.status_code, 200)
        eq_(response.get('content-type'), 'application/json')

        data = json.loads(response.content)
        eq_(len(data), 0)

    def test_search_unvouched(self):
        user = UserFactory.create(vouched=False)
        group = GroupFactory.create(visible=True)
        url = urlparams(reverse('groups:search_groups'), term=group.name)
        with self.login(user) as client:
            response = client.get(url, follow=True,
                                  **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})
        eq_(response.status_code, 200)
        eq_(response.get('content-type'), 'application/json')

    def test_search_incomplete_profile(self):
        user = UserFactory.create(vouched=False, userprofile={'full_name': ''})
        group = GroupFactory.create(visible=True)
        url = urlparams(reverse('groups:search_skills'), term=group.name)
        with self.login(user) as client:
            response = client.get(url, follow=True,
                                  **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})
        eq_(response.status_code, 200)
        eq_(response.get('content-type'), 'application/json')

    @requires_login()
    def test_search_anonymous(self):
        url = urlparams(reverse('groups:search_groups'), term='invalid')
        client = Client()
        client.get(url, follow=True)

    def test_search_skills(self):
        user = UserFactory.create()
        skill_1 = SkillFactory.create()
        SkillFactory.create()
        url = urlparams(reverse('groups:search_skills'), term=skill_1.name)
        with self.login(user) as client:
            response = client.get(url, follow=True,
                                  **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})
        eq_(response.status_code, 200)
        eq_(response.get('content-type'), 'application/json')

        data = json.loads(response.content)
        eq_(len(data), 1, 'Non autocomplete skills are included in search')
        eq_(data[0], skill_1.name)

    def test_search_no_ajax(self):
        user = UserFactory.create()
        group = GroupFactory.create()
        url = urlparams(reverse('groups:search_groups'), term=group.name)
        with self.login(user) as client:
            response = client.get(url, follow=True)
        ok_(isinstance(response, HttpResponseBadRequest))

    def test_search_no_term(self):
        user = UserFactory.create()
        url = reverse('groups:search_groups')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        ok_(isinstance(response, HttpResponseBadRequest))
