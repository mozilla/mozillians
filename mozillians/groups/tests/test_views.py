import json

from django.core.urlresolvers import reverse
from django.db.models import Count
from django.http import HttpResponseBadRequest
from django.test.client import Client, RequestFactory

from funfactory.helpers import urlparams
from mock import patch
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase, requires_login, requires_vouch
from mozillians.groups.models import Group, Skill
from mozillians.groups.tests import (GroupFactory, GroupAliasFactory,
                                     LanguageFactory, SkillFactory)
from mozillians.groups.views import _list_groups
from mozillians.users.tests import UserFactory


@patch('mozillians.groups.views.settings.ITEMS_PER_PAGE', 1)
@patch('mozillians.groups.views.render')
class ListTests(TestCase):
    def setUp(self):
        self.user = UserFactory.create(userprofile={'is_vouched': True})
        self.group_1 = GroupFactory.create()
        self.group_2 = GroupFactory.create()
        self.group_2.members.add(self.user.userprofile)
        self.query = (Group.objects
                      .filter(pk__in=[self.group_1.pk, self.group_2.pk])
                      .annotate(num_members=Count('members')))
        self.template = 'groups/index.html'
        self.request = RequestFactory()
        self.request.GET = {}
        self.request.user = self.user

    def test_list_groups(self, render_mock):
        _list_groups(self.request, self.template, self.query)
        ok_(render_mock.called)
        request, template, data = render_mock.call_args[0]
        eq_(template, self.template)
        eq_(data['groups'].paginator.count, 2)
        eq_(data['groups'].paginator.num_pages, 2)
        eq_(data['groups'].number, 1)
        eq_(data['groups'].object_list[0], self.group_1)

    def test_sort_by_name(self, render_mock):
        self.request.GET = {'sort': 'name'}
        _list_groups(self.request, self.template, self.query)
        ok_(render_mock.called)
        request, template, data = render_mock.call_args[0]
        eq_(data['groups'].object_list[0], self.group_1)

    def test_sort_by_most_members(self, render_mock):
        self.request.GET = {'sort': '-num_members'}
        _list_groups(self.request, self.template, self.query)
        ok_(render_mock.called)
        request, template, data = render_mock.call_args[0]
        eq_(data['groups'].object_list[0], self.group_2)

    def test_sort_by_fewest_members(self, render_mock):
        self.request.GET = {'sort': 'num_members'}
        _list_groups(self.request, self.template, self.query)
        ok_(render_mock.called)
        request, template, data = render_mock.call_args[0]
        eq_(data['groups'].object_list[0], self.group_1)

    def test_invalid_sort(self, render_mock):
        self.request.GET = {'sort': 'invalid'}
        _list_groups(self.request, self.template, self.query)
        ok_(render_mock.called)
        request, template, data = render_mock.call_args[0]
        eq_(data['groups'].object_list[0], self.group_1)

    def test_second_page(self, render_mock):
        self.request.GET = {'page': '2'}
        _list_groups(self.request, self.template, self.query)
        ok_(render_mock.called)
        request, template, data = render_mock.call_args[0]
        eq_(data['groups'].number, 2)

    def test_empty_page(self, render_mock):
        self.request.GET = {'page': '20000'}
        _list_groups(self.request, self.template, self.query)
        ok_(render_mock.called)
        request, template, data = render_mock.call_args[0]
        eq_(data['groups'].number, 2)

    def test_invalid_page(self, render_mock):
        self.request.GET = {'page': 'invalid'}
        _list_groups(self.request, self.template, self.query)
        ok_(render_mock.called)
        request, template, data = render_mock.call_args[0]
        eq_(data['groups'].number, 1)


class IndexTests(TestCase):
    def setUp(self):
        self.url = reverse('groups:index_groups')

    def test_index(self):
        user_1 = UserFactory.create(userprofile={'is_vouched': True})
        user_2 = UserFactory.create()
        group_1 = GroupFactory.create()
        group_2 = GroupFactory.create()
        group_3 = GroupFactory.create()
        group_1.members.add(user_1.userprofile)
        group_2.members.add(user_1.userprofile)
        group_3.members.add(user_2.userprofile)

        with self.login(user_1) as client:
            response = client.get(self.url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'groups/index_groups.html')
        eq_(set(response.context['groups'].paginator.object_list),
            set([group_1, group_2]))

    @requires_login()
    def test_index_anonymous(self):
        client = Client()
        client.get(self.url, follow=True)

    @requires_vouch()
    def test_index_unvouched(self):
        user = UserFactory.create()
        with self.login(user) as client:
            client.get(self.url, follow=True)


class IndexFunctionalAreasTests(TestCase):
    def setUp(self):
        self.url = reverse('groups:index_functional_areas')

    def test_index_functional_areas(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        group_1 = GroupFactory.create(steward=user.userprofile)
        group_2 = GroupFactory.create()
        GroupFactory.create()
        group_1.members.add(user.userprofile)
        group_2.members.add(user.userprofile)

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
        user = UserFactory.create()
        with self.login(user) as client:
            client.get(self.url, follow=True)


class IndexSkillsTests(TestCase):
    def setUp(self):
        self.url = reverse('groups:index_skills')

    def test_index_skills(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
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
        user = UserFactory.create()
        with self.login(user) as client:
            client.get(self.url, follow=True)


class SearchTests(TestCase):
    def test_search_existing_group(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        group_1 = GroupFactory.create(auto_complete=True)
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
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = urlparams(reverse('groups:search_groups'), term='invalid')
        with self.login(user) as client:
            response = client.get(url, follow=True,
                                  **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})
        eq_(response.status_code, 200)
        eq_(response.get('content-type'), 'application/json')

        data = json.loads(response.content)
        eq_(len(data), 0)

    def test_search_unvouched(self):
        user = UserFactory.create()
        group = GroupFactory.create(auto_complete=True)
        url = urlparams(reverse('groups:search_groups'), term=group.name)
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
        user = UserFactory.create(userprofile={'is_vouched': True})
        skill_1 = SkillFactory.create(auto_complete=True)
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

    def test_search_languages(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        language_1 = LanguageFactory.create(auto_complete=True)
        LanguageFactory.create()
        url = urlparams(reverse('groups:search_languages'), term=language_1.name)
        with self.login(user) as client:
            response = client.get(url, follow=True,
                                  **{'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})
        eq_(response.status_code, 200)
        eq_(response.get('content-type'), 'application/json')

        data = json.loads(response.content)
        eq_(len(data), 1, 'Non autocomplete languages are included in search')
        eq_(data[0], language_1.name)

    def test_search_no_ajax(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        group = GroupFactory.create()
        url = urlparams(reverse('groups:search_groups'), term=group.name)
        with self.login(user) as client:
            response = client.get(url, follow=True)
        ok_(isinstance(response, HttpResponseBadRequest))

    def test_search_no_term(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('groups:search_groups')
        with self.login(user) as client:
            response = client.get(url, follow=True)
        ok_(isinstance(response, HttpResponseBadRequest))


class ShowTests(TestCase):
    def setUp(self):
        self.group = GroupFactory.create()
        self.url = reverse('groups:show_group', kwargs={'url': self.group.url})
        self.user_1 = UserFactory.create(userprofile={'is_vouched': True})
        self.user_2 = UserFactory.create(userprofile={'is_vouched': True})
        self.group.members.add(self.user_2.userprofile)

    def test_show_user_not_in_group(self):
        with self.login(self.user_1) as client:
            response = client.get(self.url, follow=True)
        eq_(response.status_code, 200)
        context = response.context
        eq_(context['group'], self.group)
        eq_(context['in_group'], False)
        eq_(context['people'].paginator.count, 1)
        eq_(context['people'][0], self.user_2.userprofile)

    def test_show_user_in_group(self):
        """Test show() for a user within the group."""
        with self.login(self.user_2) as client:
            response = client.get(self.url, follow=True)
        eq_(response.status_code, 200)
        context = response.context
        eq_(context['group'], self.group)
        eq_(context['in_group'], True)
        eq_(context['people'].paginator.count, 1)
        eq_(context['people'][0], self.user_2.userprofile)

    def test_show_empty_group(self):
        group = GroupFactory.create()
        url = reverse('groups:show_group', kwargs={'url': group.url})
        with self.login(self.user_1) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        context = response.context
        eq_(context['people'].paginator.count, 0)

    @requires_login()
    def test_show_anonymous(self):
        client = Client()
        client.get(self.url, follow=True)

    @requires_vouch()
    def test_show_unvouched(self):
        user = UserFactory.create()
        with self.login(user) as client:
            client.get(self.url, follow=True)

    def test_nonexistant_group(self):
        url = reverse('groups:show_group', kwargs={'url': 'invalid'})
        with self.login(self.user_1) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 404)

    def test_alias_redirection(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        group = GroupFactory.create()
        group_alias = GroupAliasFactory.create(alias=group)
        url = reverse('groups:show_group', kwargs={'url': group_alias.url})
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['group'], group)

    def test_show_leave_group_button_value_with_steward(self):
        steward_user = UserFactory.create(userprofile={'is_vouched': True})
        group = GroupFactory.create(steward=steward_user.userprofile)
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('groups:show_group', kwargs={'url': group.url})

        with self.login(steward_user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['hide_leave_group_button'], True)

        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['hide_leave_group_button'], False)

    def test_show_leave_group_button_value_without_steward(self):
        group = GroupFactory.create()
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('groups:show_group', kwargs={'url': group.url})

        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['hide_leave_group_button'], False)

    def test_show_leave_group_button_value_skill(self):
        skill = SkillFactory.create()
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('groups:show_skill', kwargs={'url': skill.url})

        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['hide_leave_group_button'], False)


class ToggleGroupSubscriptionTests(TestCase):
    def setUp(self):
        self.group = GroupFactory.create()
        # We must request the full path, with language, or the
        # LanguageMiddleware will convert the request to GET.
        self.url = reverse('groups:toggle_group_subscription', prefix='/en-US/',
                           kwargs={'url': self.group.url})
        self.user = UserFactory.create(userprofile={'is_vouched': True})

    @patch('mozillians.groups.views.update_basket_task.delay')
    def test_group_subscription(self, basket_task_mock):
        with self.login(self.user) as client:
            client.post(self.url, follow=True)
        group = Group.objects.get(id=self.group.id)
        ok_(group.members.filter(id=self.user.userprofile.id).exists())
        basket_task_mock.assert_called_with(self.user.userprofile.id)

    @patch('mozillians.groups.views.update_basket_task.delay')
    def test_group_unsubscription(self, basket_task_mock):
        self.group.members.add(self.user.userprofile)
        with self.login(self.user) as client:
            client.post(self.url, follow=True)
        group = Group.objects.get(id=self.group.id)
        ok_(not group.members.filter(id=self.user.userprofile.id).exists())
        basket_task_mock.assert_called_with(self.user.userprofile.id)

    def test_nonexistant_group(self):
        url = reverse('groups:toggle_group_subscription', prefix='/en-US/',
                      kwargs={'url': 'invalid'})
        with self.login(self.user) as client:
            response = client.post(url, follow=True)
        eq_(response.status_code, 404)

    def test_get(self):
        url = reverse('groups:toggle_group_subscription',
                      kwargs={'url': self.group.url})
        with self.login(self.user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 405)

    @requires_vouch()
    def test_unvouched(self):
        user = UserFactory.create()
        with self.login(user) as client:
            client.post(self.url, follow=True)

    @requires_login()
    def test_anonymous(self):
        client = Client()
        client.post(self.url, follow=True)

    def test_system_group(self):
        system_group = GroupFactory.create(system=True)
        url = reverse('groups:toggle_group_subscription', prefix='/en-US/',
                      kwargs={'url': system_group.url})
        with self.login(self.user) as client:
            client.post(url, follow=True)
        system_group = Group.objects.get(id=system_group.id)
        ok_(not system_group.members.filter(pk=self.user.pk).exists())


class ToggleSkillSubscriptionTests(TestCase):
    def setUp(self):
        self.skill = SkillFactory.create()
        # We must request the full path, with language, or the
        # LanguageMiddleware will convert the request to GET.
        self.url = reverse('groups:toggle_skill_subscription', prefix='/en-US/',
                           kwargs={'url': self.skill.url})
        self.user = UserFactory.create(userprofile={'is_vouched': True})

    def test_skill_subscription(self):
        with self.login(self.user) as client:
            client.post(self.url, follow=True)
        skill = Skill.objects.get(id=self.skill.id)
        ok_(skill.members.filter(id=self.user.userprofile.id).exists())

    def test_skill_unsubscription(self):
        self.skill.members.add(self.user.userprofile)
        with self.login(self.user) as client:
            client.post(self.url, follow=True)
        skill = Skill.objects.get(id=self.skill.id)
        ok_(not skill.members.filter(id=self.user.userprofile.id).exists())

    def test_nonexistant_skill(self):
        url = reverse('groups:toggle_skill_subscription', prefix='/en-US/',
                      kwargs={'url': 'invalid'})
        with self.login(self.user) as client:
            response = client.post(url, follow=True)
        eq_(response.status_code, 404)

    def test_get(self):
        url = reverse('groups:toggle_skill_subscription',
                      kwargs={'url': self.skill.url})
        with self.login(self.user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 405)

    @requires_vouch()
    def test_unvouched(self):
        user = UserFactory.create()
        with self.login(user) as client:
            client.post(self.url, follow=True)

    @requires_login()
    def test_anonymous(self):
        client = Client()
        client.post(self.url, follow=True)
