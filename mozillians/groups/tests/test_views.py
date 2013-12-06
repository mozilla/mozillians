import json

from django.core.urlresolvers import reverse
from django.db.models import Count
from django.http import HttpResponseBadRequest
from django.test.client import Client, RequestFactory

from funfactory.helpers import urlparams
from mock import patch
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase, requires_login, requires_vouch
from mozillians.groups.models import Group, GroupAlias, GroupMembership, Skill
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
        self.group_2.add_member(self.user.userprofile)
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
        user_3 = UserFactory.create(userprofile={'is_vouched': True})
        group_1 = GroupFactory.create()
        group_2 = GroupFactory.create()
        group_3 = GroupFactory.create()
        group_1.add_member(user_1.userprofile)
        group_1.add_member(user_3.userprofile)
        group_2.add_member(user_1.userprofile)
        group_3.add_member(user_2.userprofile)

        with self.login(user_1) as client:
            response = client.get(self.url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'groups/index_groups.html')
        eq_(set(response.context['groups'].paginator.object_list),
            set([group_1, group_2]))

        # Member counts
        group1 = response.context['groups'].paginator.object_list.get(pk=group_1.pk)
        eq_(group1.num_members, 2)

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
        group_1 = GroupFactory.create(curator=user.userprofile,
                                      functional_area=True)
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
        group = GroupFactory.create(visible=True)
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

    def test_search_languages(self):
        user = UserFactory.create(userprofile={'is_vouched': True})
        language_1 = LanguageFactory.create()
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
        self.group.add_member(self.user_2.userprofile)

    def test_show_user_not_in_group(self):
        with self.login(self.user_1) as client:
            response = client.get(self.url, follow=True)
        eq_(response.status_code, 200)
        context = response.context
        eq_(context['group'], self.group)
        eq_(context['in_group'], False)
        eq_(context['people'].paginator.count, 1)
        eq_(context['people'][0], self.user_2.userprofile)
        eq_(context['people'][0].pending, False)

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

    def test_show_pending_user(self):
        self.group.add_member(self.user_2.userprofile, GroupMembership.PENDING)
        with self.login(self.user_2) as client:
            response = client.get(self.url, follow=True)
        eq_(response.status_code, 200)
        context = response.context
        eq_(context['group'], self.group)
        eq_(context['in_group'], False)
        eq_(context['people'].paginator.count, 1)
        eq_(context['people'][0], self.user_2.userprofile)
        eq_(context['people'][0].pending, True)

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

    def test_show_leave_button_value_with_curator(self):
        curator_user = UserFactory.create(userprofile={'is_vouched': True})
        group = GroupFactory.create(curator=curator_user.userprofile)
        user = UserFactory.create(userprofile={'is_vouched': True})
        group.add_member(user.userprofile)
        url = reverse('groups:show_group', kwargs={'url': group.url})

        with self.login(curator_user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['show_leave_button'], False)

        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['show_leave_button'], True)

    def test_show_leave_button_value_without_curator(self):
        group = GroupFactory.create()
        user = UserFactory.create(userprofile={'is_vouched': True})
        group.add_member(user.userprofile)
        url = reverse('groups:show_group', kwargs={'url': group.url})

        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['show_leave_button'], True)

    def test_show_leave_button_value_members_cant_leave(self):
        """
        Don't show leave button for a group whose members_can_leave flag
        is False, even for group member
        """
        group = GroupFactory.create(members_can_leave=False)
        user = UserFactory.create(userprofile={'is_vouched': True})
        group.add_member(user.userprofile)
        url = reverse('groups:show_group', kwargs={'url': group.url})

        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['show_leave_button'], False)

    def test_show_leave_button_value_members_can_leave(self):
        """
        Do show leave button for a group whose members_can_leave flag
        is True, for group member
        """
        group = GroupFactory.create(members_can_leave=True)
        user = UserFactory.create(userprofile={'is_vouched': True})
        group.add_member(user.userprofile)
        url = reverse('groups:show_group', kwargs={'url': group.url})

        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['show_leave_button'], True)

    def test_show_leave_button_value_members_can_leave_non_member(self):
        """
        Don't show leave button for a group whose members_can_leave flag
        is True, if not group member
        """
        group = GroupFactory.create(members_can_leave=True)
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('groups:show_group', kwargs={'url': group.url})

        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['show_leave_button'], False)

    def test_show_join_button_accepting_members_yes(self):
        group = GroupFactory.create(accepting_new_members='yes')
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('groups:show_group', kwargs={'url': group.url})

        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['show_join_button'], True)

    def test_show_join_button_accepting_members_yes_member(self):
        group = GroupFactory.create(accepting_new_members='yes')
        user = UserFactory.create(userprofile={'is_vouched': True})
        group.add_member(user.userprofile)
        url = reverse('groups:show_group', kwargs={'url': group.url})

        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['show_join_button'], False)

    def test_show_join_button_accepting_members_by_request(self):
        group = GroupFactory.create(accepting_new_members='yes')
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('groups:show_group', kwargs={'url': group.url})

        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['show_join_button'], True)

    def test_show_join_button_accepting_members_by_request_member(self):
        group = GroupFactory.create(accepting_new_members='yes')
        user = UserFactory.create(userprofile={'is_vouched': True})
        group.add_member(user.userprofile)
        url = reverse('groups:show_group', kwargs={'url': group.url})

        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['show_join_button'], False)

    def test_show_join_button_accepting_members_no(self):
        group = GroupFactory.create(accepting_new_members='no')
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('groups:show_group', kwargs={'url': group.url})

        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['show_join_button'], False)

    def test_show_leave_button_value_skill(self):
        skill = SkillFactory.create()
        user = UserFactory.create(userprofile={'is_vouched': True})
        skill.members.add(user.userprofile)
        url = reverse('groups:show_skill', kwargs={'url': skill.url})

        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['show_leave_button'], True)

    def test_remove_button_confirms(self):
        """GET to remove_member view displays confirmation"""
        # Make user 1 the group curator so they can remove users
        self.group.curator = self.user_1.userprofile
        self.group.save()

        # We must request the full path, with language, or the
        # LanguageMiddleware will convert the request to GET.
        url = reverse('groups:remove_member', prefix='/en-US/',
                      kwargs=dict(group_pk=self.group.pk, user_pk=self.user_2.userprofile.pk))
        with self.login(self.user_1) as client:
            response = client.get(url, follow=True)
        self.assertTemplateUsed(response, 'groups/confirm_remove_member.html')
        # Still a member
        ok_(self.group.has_member(self.user_2.userprofile))

    def test_post_remove_button_removes(self):
        """POST to remove_member view removes member"""
        # Make user 1 the group curator so they can remove users
        self.group.curator = self.user_1.userprofile
        self.group.save()

        # We must request the full path, with language, or the
        # LanguageMiddleware will convert the request to GET.
        url = reverse('groups:remove_member', prefix='/en-US/',
                      kwargs=dict(group_pk=self.group.pk, user_pk=self.user_2.userprofile.pk))
        with self.login(self.user_1) as client:
            response = client.post(url, follow=True)
        self.assertTemplateNotUsed(response, 'groups/confirm_remove_member.html')
        # Not a member anymore
        ok_(not self.group.has_member(self.user_2.userprofile))

    def test_confirm_user(self):
        """POST to confirm user view changes member from pending to member"""
        # Make user 1 the group curator so they can remove users
        self.group.curator = self.user_1.userprofile
        self.group.save()
        # Make user 2 pending
        self.group.add_member(self.user_2.userprofile, GroupMembership.PENDING)
        ok_(self.group.has_pending_member(self.user_2.userprofile))

        # We must request the full path, with language, or the
        # LanguageMiddleware will convert the request to GET.
        url = reverse('groups:confirm_member', prefix='/en-US/',
                      kwargs=dict(group_pk=self.group.pk, user_pk=self.user_2.userprofile.pk))
        with self.login(self.user_1) as client:
            response = client.post(url, follow=True)
        self.assertTemplateNotUsed(response, 'groups/confirm_remove_member.html')
        # Now a member
        ok_(self.group.has_member(self.user_2.userprofile))


class ToggleGroupSubscriptionTests(TestCase):
    def setUp(self):
        self.group = GroupFactory.create()
        self.user = UserFactory.create(userprofile={'is_vouched': True})
        # We must request the full path, with language, or the
        # LanguageMiddleware will convert the request to GET.
        self.join_url = reverse('groups:join_group', prefix='/en-US/',
                                kwargs={'group_pk': self.group.pk})
        self.leave_url = reverse('groups:remove_member', prefix='/en-US/',
                                 kwargs={'group_pk': self.group.pk,
                                         'user_pk': self.user.userprofile.pk})

    @patch('mozillians.groups.models.update_basket_task.delay')
    def test_group_subscription(self, basket_task_mock):
        with self.login(self.user) as client:
            client.post(self.join_url, follow=True)
        group = Group.objects.get(id=self.group.id)
        ok_(group.members.filter(id=self.user.userprofile.id).exists())
        basket_task_mock.assert_called_with(self.user.userprofile.id)

    @patch('mozillians.groups.models.update_basket_task.delay')
    def test_group_unsubscription(self, basket_task_mock):
        self.group.add_member(self.user.userprofile)
        with self.login(self.user) as client:
            client.post(self.leave_url, follow=True)
        group = Group.objects.get(id=self.group.id)
        ok_(not group.members.filter(id=self.user.userprofile.id).exists())
        basket_task_mock.assert_called_with(self.user.userprofile.id)

    def test_nonexistant_group(self):
        url = reverse('groups:join_group', prefix='/en-US/',
                      kwargs={'group_pk': 32097})
        with self.login(self.user) as client:
            response = client.post(url, follow=True)
        eq_(response.status_code, 404)

    @requires_vouch()
    def test_unvouched(self):
        user = UserFactory.create()
        join_url = reverse('groups:join_group', prefix='/en-US/',
                           kwargs={'group_pk': self.group.pk})
        with self.login(user) as client:
            client.post(join_url, follow=True)

    @requires_login()
    def test_anonymous(self):
        client = Client()
        client.post(self.join_url, follow=True)

    def test_unjoinable_group(self):
        group = GroupFactory.create(accepting_new_members='no')
        join_url = reverse('groups:join_group', prefix='/en-US/',
                           kwargs={'group_pk': group.pk})
        with self.login(self.user) as client:
            client.post(join_url, follow=True)
        group = Group.objects.get(id=group.id)
        ok_(not group.members.filter(pk=self.user.pk).exists())


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


class CreateGroupTests(TestCase):
    def setUp(self):
        self.user = UserFactory.create(
            userprofile={'is_vouched': True})

    def test_basic_group_creation_as_superuser(self):
        # superuser have access to all group parameters when creating a group
        self.user.is_superuser = True
        self.user.save()
        url = reverse('groups:group_add', prefix='/en-US/')
        data = {
            'name': u'Test Group',
            'accepting_new_members': u'by_request',
            'description': u'lorem ipsum and lah-dee-dah',
            'irc_channel': u'some text, this is not validated',
            'website': u'http://mozillians.org',
            'wiki': u'http://wiki.mozillians.org',
            'members_can_leave': 'checked',
            'visible': 'checked',
            # 'functional_area' not checked
        }
        with self.login(self.user) as client:
            response = client.post(url, data=data, follow=False)
        eq_(302, response.status_code)
        group = GroupAlias.objects.get(name=data['name']).alias
        eq_(u'by_request', group.accepting_new_members)
        ok_(group.members_can_leave)
        ok_(group.visible)
        ok_(not group.functional_area)
        eq_(data['description'], group.description)
        eq_(data['irc_channel'], group.irc_channel)
        # URLs get '/' added, I'm not sure why
        eq_(data['website'] + '/', group.website)
        eq_(data['wiki'] + '/', group.wiki)

    def test_basic_group_creation_as_non_superuser(self):
        # non-superuser cannot set some of the parameters, try though they might
        url = reverse('groups:group_add', prefix='/en-US/')
        data = {
            'name': u'Test Group',
            'description': u'lorem ipsum and lah-dee-dah',
            'irc_channel': u'some text, this is not validated',
            'website': u'http://mozillians.org',
            'wiki': u'http://wiki.mozillians.org',
            #'members_can_leave': not checked
            #'visible': not checked
            'functional_area': 'checked',  # should be ignored
            'accepting_new_members': u'barracuda',  # should be ignored
        }
        with self.login(self.user) as client:
            response = client.post(url, data=data, follow=False)
        eq_(302, response.status_code)
        group = GroupAlias.objects.get(name=data['name']).alias
        eq_(u'by_request', group.accepting_new_members)
        # All non-superuser-created groups are leavable by default
        ok_(group.members_can_leave)
        # All non-superuser-created groups are visible by default
        ok_(group.visible)
        # Ignored attempt to make this a functional_area by a non-superuser
        ok_(not group.functional_area)
        eq_(data['description'], group.description)
        eq_(data['irc_channel'], group.irc_channel)
        # URLs get '/' added, I'm not sure why
        eq_(data['website'] + '/', group.website)
        eq_(data['wiki'] + '/', group.wiki)

    def test_group_edit(self):
        # Curator can edit a group and change (some of) its properties
        data = {
            'name': u'Test Group',
            'accepting_new_members': u'by_request',
            'description': u'lorem ipsum and lah-dee-dah',
            'irc_channel': u'some text, this is not validated',
            'website': u'http://mozillians.org',
            'wiki': u'http://wiki.mozillians.org',
            'members_can_leave': True,
            'visible': True,
            'functional_area': False,
        }
        group = GroupFactory(**data)
        # Must be curator or superuser to edit group. Make user the curator.
        group.curator = self.user.userprofile
        group.save()
        url = reverse('groups:group_edit', prefix='/en-US/', kwargs={'url': group.url})
        # Change some data
        data2 = data.copy()
        data2['description'] = u'A new description'
        data2['wiki'] = u'http://google.com/'
        # make like a form
        del data2['functional_area']
        with self.login(self.user) as client:
            response = client.post(url, data=data2, follow=False)
        eq_(302, response.status_code)
        group = GroupAlias.objects.get(name=data['name']).alias
        eq_(data2['description'], group.description)
        ok_(group.visible)
        ok_(group.members_can_leave)
        ok_(not group.functional_area)
