from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test.utils import override_script_prefix

from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase, requires_login, requires_vouch
from mozillians.groups.models import Group, GroupMembership, Skill
from mozillians.groups.tests import (GroupFactory, SkillFactory)
from mozillians.users.tests import UserFactory


class ToggleGroupSubscriptionTests(TestCase):
    def setUp(self):
        self.group = GroupFactory.create()
        self.user = UserFactory.create()
        # We must request the full path, with language, or the
        # LanguageMiddleware will convert the request to GET.
        with override_script_prefix('/en-US/'):
            self.join_url = reverse('groups:join_group',
                                    kwargs={'url': self.group.url})
            self.leave_url = reverse('groups:remove_member',
                                     kwargs={'url': self.group.url,
                                             'user_pk': self.user.userprofile.pk})

    def test_group_subscription(self):
        with self.login(self.user) as client:
            client.post(self.join_url, follow=True)
        group = Group.objects.get(id=self.group.id)
        ok_(group.members.filter(id=self.user.userprofile.id).exists())

    def test_group_subscription_terms(self):
        group = GroupFactory.create(terms='Example terms')
        with override_script_prefix('/en-US/'):
            join_url = reverse('groups:join_group', kwargs={'url': group.url})
        with self.login(self.user) as client:
            client.post(join_url, follow=True)

        membership = group.groupmembership_set.get(userprofile=self.user.userprofile)
        eq_(membership.status, GroupMembership.PENDING_TERMS)

    def test_group_subscription_terms_by_request(self):
        group = GroupFactory.create(accepting_new_members='by_request', terms='Example terms')
        with override_script_prefix('/en-US/'):
            join_url = reverse('groups:join_group', kwargs={'url': group.url})
        with self.login(self.user) as client:
            client.post(join_url, follow=True)

        membership = group.groupmembership_set.get(userprofile=self.user.userprofile)
        eq_(membership.status, GroupMembership.PENDING)

    def test_group_unsubscription(self):
        self.group.add_member(self.user.userprofile)
        with self.login(self.user) as client:
            client.post(self.leave_url, follow=True)
        group = Group.objects.get(id=self.group.id)
        ok_(not group.members.filter(id=self.user.userprofile.id).exists())

    def test_nonexistant_group(self):
        with override_script_prefix('/en-US/'):
            url = reverse('groups:join_group', kwargs={'url': 'woohoo'})
        with self.login(self.user) as client:
            response = client.post(url, follow=True)
        eq_(response.status_code, 404)

    @requires_vouch()
    def test_unvouched(self):
        user = UserFactory.create(vouched=False)
        with override_script_prefix('/en-US/'):
            join_url = reverse('groups:join_group',
                               kwargs={'url': self.group.url})
        with self.login(user) as client:
            client.post(join_url, follow=True)

    @requires_login()
    def test_anonymous(self):
        client = Client()
        client.post(self.join_url, follow=True)

    def test_unjoinable_group(self):
        group = GroupFactory.create(accepting_new_members='no')
        with override_script_prefix('/en-US/'):
            join_url = reverse('groups:join_group',
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
        with override_script_prefix('/en-US/'):
            self.url = reverse('groups:toggle_skill_subscription',
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
        with override_script_prefix('/en-US/'):
            url = reverse('groups:toggle_skill_subscription',
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
