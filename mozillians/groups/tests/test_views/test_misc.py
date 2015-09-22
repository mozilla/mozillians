from django.core.urlresolvers import reverse
from django.test.client import Client

from mock import patch
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase, requires_login, requires_vouch
from mozillians.groups.models import Group, GroupAlias, GroupMembership, Skill
from mozillians.groups.tests import (GroupFactory, SkillFactory)
from mozillians.users.tests import UserFactory


class ToggleGroupSubscriptionTests(TestCase):
    def setUp(self):
        self.group = GroupFactory.create()
        self.user = UserFactory.create()
        # We must request the full path, with language, or the
        # LanguageMiddleware will convert the request to GET.
        self.join_url = reverse('groups:join_group', prefix='/en-US/',
                                kwargs={'url': self.group.url})
        self.leave_url = reverse('groups:remove_member', prefix='/en-US/',
                                 kwargs={'url': self.group.url,
                                         'user_pk': self.user.userprofile.pk})

    @patch('mozillians.groups.models.update_basket_task.delay')
    def test_group_subscription(self, basket_task_mock):
        with self.login(self.user) as client:
            client.post(self.join_url, follow=True)
        group = Group.objects.get(id=self.group.id)
        ok_(group.members.filter(id=self.user.userprofile.id).exists())
        basket_task_mock.assert_called_with(self.user.userprofile.id)

    @patch('mozillians.groups.models.update_basket_task.delay')
    def test_group_subscription_terms(self, basket_task_mock):
        group = GroupFactory.create(terms='Example terms')
        join_url = reverse('groups:join_group', prefix='/en-US/', kwargs={'url': group.url})
        with self.login(self.user) as client:
            client.post(join_url, follow=True)

        membership = group.groupmembership_set.get(userprofile=self.user.userprofile)
        eq_(membership.status, GroupMembership.PENDING_TERMS)
        basket_task_mock.assert_called_with(self.user.userprofile.id)

    @patch('mozillians.groups.models.update_basket_task.delay')
    def test_group_subscription_terms_by_request(self, basket_task_mock):
        group = GroupFactory.create(accepting_new_members='by_request', terms='Example terms')
        join_url = reverse('groups:join_group', prefix='/en-US/', kwargs={'url': group.url})
        with self.login(self.user) as client:
            client.post(join_url, follow=True)

        membership = group.groupmembership_set.get(userprofile=self.user.userprofile)
        eq_(membership.status, GroupMembership.PENDING)
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
                      kwargs={'url': 'woohoo'})
        with self.login(self.user) as client:
            response = client.post(url, follow=True)
        eq_(response.status_code, 404)

    @requires_vouch()
    def test_unvouched(self):
        user = UserFactory.create(vouched=False)
        join_url = reverse('groups:join_group', prefix='/en-US/',
                           kwargs={'url': self.group.url})
        with self.login(user) as client:
            client.post(join_url, follow=True)

    @requires_login()
    def test_anonymous(self):
        client = Client()
        client.post(self.join_url, follow=True)

    def test_unjoinable_group(self):
        group = GroupFactory.create(accepting_new_members='no')
        join_url = reverse('groups:join_group', prefix='/en-US/',
                           kwargs={'url': group.url})
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
        self.user = UserFactory.create()

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
        user = UserFactory.create(vouched=False)
        with self.login(user) as client:
            client.post(self.url, follow=True)

    @requires_login()
    def test_anonymous(self):
        client = Client()
        client.post(self.url, follow=True)


class CreateGroupTests(TestCase):
    def test_basic_group_creation_as_manager(self):
        # Managers have access to all group parameters when creating a group
        user = UserFactory.create(manager=True)
        url = reverse('groups:group_add', prefix='/en-US/')
        data = {
            'name': u'Test Group',
            'accepting_new_members': u'by_request',
            'new_member_criteria': u'some criteria',
            'description': u'lorem ipsum and lah-dee-dah',
            'irc_channel': u'some text, this is not validated',
            'website': u'http://mozillians.org',
            'wiki': u'http://wiki.mozillians.org',
            'members_can_leave': 'checked',
            'visible': 'checked',
            'curators': [user.userprofile.id]
            # 'functional_area' not checked
        }
        with self.login(user) as client:
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

    def test_basic_group_creation_as_non_manager(self):
        # non-managers cannot set some of the parameters, try though they might
        user = UserFactory.create()
        url = reverse('groups:group_add', prefix='/en-US/')
        data = {
            'name': u'Test Group',
            'description': u'lorem ipsum and lah-dee-dah',
            'irc_channel': u'some text, this is not validated',
            'website': u'http://mozillians.org',
            'wiki': u'http://wiki.mozillians.org',
            # 'members_can_leave': not checked
            # 'visible': not checked
            'functional_area': 'checked',  # should be ignored
            'accepting_new_members': 'yes',
            'members_can_leave': False,  # should be ignored
            'curators': [user.userprofile.id]
        }
        with self.login(user) as client:
            response = client.post(url, data=data, follow=False)
        eq_(302, response.status_code)
        group = GroupAlias.objects.get(name=data['name']).alias
        eq_(u'yes', group.accepting_new_members)
        # All non-manager-created groups are leavable by default
        ok_(group.members_can_leave)
        # All non-manager-created groups are visible by default
        ok_(group.visible)
        # Ignored attempt to make this a functional_area by a non-manager
        ok_(not group.functional_area)
        eq_(data['description'], group.description)
        eq_(data['irc_channel'], group.irc_channel)
        # URLs get '/' added, I'm not sure why
        eq_(data['website'] + '/', group.website)
        eq_(data['wiki'] + '/', group.wiki)

    def test_basic_group_creation_with_terms(self):
        # Curator accepts terms by default
        user = UserFactory.create(manager=True)
        url = reverse('groups:group_add', prefix='/en-US/')
        data = {
            'name': u'Test Group',
            'accepting_new_members': u'by_request',
            'new_member_criteria': u'some criteria',
            'description': u'lorem ipsum and lah-dee-dah',
            'irc_channel': u'some text, this is not validated',
            'website': u'http://mozillians.org',
            'wiki': u'http://wiki.mozillians.org',
            'members_can_leave': 'checked',
            'visible': 'checked',
            'terms': 'Example terms',
            'curators': [user.id]
        }
        with self.login(user) as client:
            response = client.post(url, data=data, follow=False)
        eq_(302, response.status_code)
        group = GroupAlias.objects.get(name=data['name']).alias
        eq_(group.terms, 'Example terms')
        membership = GroupMembership.objects.get(group=group, userprofile=user.userprofile)
        eq_(membership.status, GroupMembership.MEMBER)

    def test_group_edit(self):
        # Curator can edit a group and change (some of) its properties
        user = UserFactory.create()
        data = {
            'name': u'Test Group',
            'accepting_new_members': u'by_request',
            'new_member_criteria': 'some criteria',
            'description': u'lorem ipsum and lah-dee-dah',
            'irc_channel': u'some text, this is not validated',
            'website': u'http://mozillians.org',
            'wiki': u'http://wiki.mozillians.org',
            'members_can_leave': True,
            'visible': True,
            'functional_area': False,
            'curators': [user.userprofile.id]
        }
        group = GroupFactory(**data)
        group.curators.add(user.userprofile)
        url = reverse('groups:group_edit', prefix='/en-US/', kwargs={'url': group.url})
        # Change some data
        data2 = data.copy()
        data2['description'] = u'A new description'
        data2['wiki'] = u'http://google.com/'
        # make like a form
        del data2['functional_area']
        with self.login(user) as client:
            response = client.post(url, data=data2, follow=False)
        eq_(302, response.status_code)
        group = GroupAlias.objects.get(name=data['name']).alias
        eq_(data2['description'], group.description)
        ok_(group.visible)
        ok_(group.members_can_leave)
        ok_(not group.functional_area)
