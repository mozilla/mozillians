from django.test import RequestFactory

from mock import patch, MagicMock
from nose.tools import ok_

from mozillians.common.tests import TestCase
from mozillians.groups.models import Group, GroupAlias, GroupMembership
from mozillians.groups.tests import GroupFactory
from mozillians.groups.views import show, group_delete
from mozillians.users.tests import UserFactory


class ShowGroupDeleteTests(TestCase):
    """
    Test the show group view with regard to when it displays the delete group button.
    """
    def setUp(self):
        self.group = GroupFactory.create()
        self.user = UserFactory.create()
        self.factory = RequestFactory()

    def get_context(self, group):
        """
        Call the show group view method on the group, and return the context that it
        would have used to render the page
        """
        request = self.factory.get('/')
        request.user = self.user
        request._messages = MagicMock()

        with patch('mozillians.groups.views.render') as mock_render:
            with patch('django.views.decorators.cache.add_never_cache_headers'):
                show(request, self.group.url, GroupAlias, 'groups/group.html')

        ok_(mock_render.called)
        args, kwargs = mock_render.call_args
        request, template, context = args
        return context

    def test_curator_and_no_other_members(self):
        # If curator only member, show delete button
        self.group.curators.add(self.user.userprofile)
        self.group.save()
        self.group.add_member(self.user.userprofile, GroupMembership.MEMBER)

        context = self.get_context(self.group)

        ok_('show_delete_group_button' in context)
        ok_(context['show_delete_group_button'])

    def test_curator_and_another_member(self):
        # If curator not only member, don't show delete button
        self.group.curator = self.user.userprofile
        self.group.save()
        self.group.add_member(self.user.userprofile, GroupMembership.MEMBER)
        self.group.add_member(UserFactory.create().userprofile,
                              GroupMembership.PENDING)

        context = self.get_context(self.group)

        ok_('show_delete_group_button' in context)
        ok_(not context['show_delete_group_button'])

    def test_not_curator(self):
        # Only one member (user2) but user requesting the view (user1) is not the curator
        # (actually, nobody is the curator). Don't show delete button.
        user2 = UserFactory.create()
        self.group.add_member(user2.userprofile, GroupMembership.MEMBER)

        context = self.get_context(self.group)

        ok_('show_delete_group_button' in context)
        ok_(not context['show_delete_group_button'])


class GroupDeleteTest(TestCase):
    """
    Test the group deletion view.
    """
    def setUp(self):
        self.group = GroupFactory.create()
        self.user = UserFactory.create()
        self.factory = RequestFactory()

    def test_curator_only_member(self):
        # If user is curator and no other members, can delete the group
        self.group.curators.add(self.user.userprofile)
        self.group.save()
        self.group.add_member(self.user.userprofile, GroupMembership.MEMBER)

        request = self.factory.post('/')
        request.user = self.user
        request._messages = MagicMock()

        group_delete(request, self.group.url)

        # The group was deleted
        ok_(not Group.objects.filter(url=self.group.url).exists())

    def test_multiple_members(self):
        # If there are other members, cannot delete
        self.group.curators.add(self.user.userprofile)
        self.group.add_member(self.user.userprofile, GroupMembership.MEMBER)
        self.group.add_member(UserFactory.create().userprofile,
                              GroupMembership.PENDING)

        request = self.factory.post('/')
        request.user = self.user
        request._messages = MagicMock()

        group_delete(request, self.group.url)

        # The group was NOT deleted
        ok_(Group.objects.filter(url=self.group.url).exists())

    def test_not_curator(self):
        # Only one member (user2) but user requesting the view (user1) is not the curator
        # (actually, nobody is the curator)
        user2 = UserFactory.create()
        self.group.add_member(user2.userprofile, GroupMembership.MEMBER)

        request = self.factory.post('/')
        request.user = self.user
        request._messages = MagicMock()

        group_delete(request, self.group.url)

        # The group was NOT deleted
        ok_(Group.objects.filter(url=self.group.url).exists())

    def test_is_manager(self):
        # Test that manager can delete group.
        manager = UserFactory.create(manager=True)
        user2 = UserFactory.create()
        self.group.add_member(user2.userprofile, GroupMembership.MEMBER)

        request = self.factory.post('/')
        request.user = manager
        request._messages = MagicMock()

        group_delete(request, self.group.url)

        # The group was deleted
        ok_(not Group.objects.filter(url=self.group.url).exists())
