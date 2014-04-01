from django.core.urlresolvers import reverse
from django.test import Client
from mozillians.common.tests import TestCase, requires_login, requires_vouch
from mozillians.groups.models import GroupMembership
from mozillians.groups.tests import GroupFactory, GroupAliasFactory
from mozillians.users.tests import UserFactory
from nose.tools import eq_, ok_


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
        eq_(context['page'].paginator.count, 1)
        eq_(context['page'][0].userprofile, self.user_2.userprofile)
        ok_(context['page'][0].status != GroupMembership.PENDING)
        ok_(not context['is_pending'])

    def test_show_user_in_group(self):
        """Test show() for a user within the group."""
        with self.login(self.user_2) as client:
            response = client.get(self.url, follow=True)
        eq_(response.status_code, 200)
        context = response.context
        eq_(context['group'], self.group)
        eq_(context['in_group'], True)
        eq_(context['page'].paginator.count, 1)
        eq_(context['page'][0].userprofile, self.user_2.userprofile)
        ok_(not context['is_pending'])

    def test_show_pending_user(self):
        # Make user 2 pending
        GroupMembership.objects.filter(userprofile=self.user_2.userprofile,
                                       group=self.group).update(status=GroupMembership.PENDING)
        with self.login(self.user_2) as client:
            response = client.get(self.url, follow=True)
        eq_(response.status_code, 200)
        context = response.context
        eq_(context['group'], self.group)
        eq_(context['in_group'], False)
        eq_(context['page'].paginator.count, 1)
        eq_(context['page'][0].userprofile, self.user_2.userprofile)
        eq_(context['page'][0].status, GroupMembership.PENDING)
        ok_(context['is_pending'])

    def test_show_empty_group(self):
        group = GroupFactory.create()
        url = reverse('groups:show_group', kwargs={'url': group.url})
        with self.login(self.user_1) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        context = response.context
        eq_(context['page'].paginator.count, 0)
        ok_(not context['is_pending'])

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
        ok_(not response.context['is_pending'])

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
        ok_(not response.context['is_pending'])

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
        ok_(not response.context['is_pending'])

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
        ok_(not response.context['is_pending'])

    def test_show_join_button_accepting_members_yes(self):
        group = GroupFactory.create(accepting_new_members='yes')
        user = UserFactory.create(userprofile={'is_vouched': True})
        url = reverse('groups:show_group', kwargs={'url': group.url})

        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(response.context['show_join_button'], True)
        ok_(not response.context['is_pending'])

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
        GroupMembership.objects.filter(userprofile=self.user_2.userprofile,
                                       group=self.group).update(status=GroupMembership.PENDING)
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

    def test_filter_members_only(self):
        """Filter `m` will filter out members that are only pending"""
        # Make user 1 the group curator so they can see requests
        self.group.curator = self.user_1.userprofile
        self.group.save()
        # Make user 2 a full member
        self.group.add_member(self.user_2.userprofile, GroupMembership.MEMBER)
        member = self.user_2.userprofile
        # Make user 3 a pending member
        self.user_3 = UserFactory.create(userprofile={'is_vouched': True})
        self.group.add_member(self.user_3.userprofile, GroupMembership.PENDING)
        pending = self.user_3.userprofile

        url = self.url + "?m"
        with self.login(self.user_1) as client:
            response = client.get(url, follow=True)
        people = [membership.userprofile
                  for membership in response.context['page'].object_list]
        ok_(member in people)
        ok_(pending not in people)

    def test_filter_pending_only(self):
        """Filter `r` will show only member requests (pending)"""
        # Make user 1 the group curator so they can see requests
        self.group.curator = self.user_1.userprofile
        self.group.save()
        # Make user 2 a full member
        self.group.add_member(self.user_2.userprofile, GroupMembership.MEMBER)
        member = self.user_2.userprofile
        # Make user 3 a pending member
        self.user_3 = UserFactory.create(userprofile={'is_vouched': True})
        self.group.add_member(self.user_3.userprofile, GroupMembership.PENDING)
        pending = self.user_3.userprofile

        url = self.url + "?r"
        with self.login(self.user_1) as client:
            response = client.get(url, follow=True)
        people = [membership.userprofile
                  for membership in response.context['page'].object_list]
        ok_(member not in people)
        ok_(pending in people)

    def test_filter_both(self):
        """If they specify both filters, they get all the members"""
        # Make user 1 the group curator so they can see requests
        self.group.curator = self.user_1.userprofile
        self.group.save()
        # Make user 2 a full member
        self.group.add_member(self.user_2.userprofile, GroupMembership.MEMBER)
        member = self.user_2.userprofile
        # Make user 3 a pending member
        self.user_3 = UserFactory.create(userprofile={'is_vouched': True})
        self.group.add_member(self.user_3.userprofile, GroupMembership.PENDING)
        pending = self.user_3.userprofile

        url = self.url + "?r&m"
        with self.login(self.user_1) as client:
            response = client.get(url, follow=True)
        people = [membership.userprofile
                  for membership in response.context['page'].object_list]
        ok_(member in people, people)
        ok_(pending in people)
