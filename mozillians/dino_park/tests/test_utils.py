from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from nose.tools import eq_

from mozillians.common.tests import TestCase
from mozillians.dino_park.utils import UserAccessLevel
from mozillians.groups.models import GroupMembership
from mozillians.groups.tests import GroupFactory
from mozillians.users.tests import UserFactory


class TestUserAccessScopes(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_public_access_scope(self):
        request = self.factory.get('/')
        request.user = AnonymousUser()
        eq_(UserAccessLevel.get_privacy(request), 'public')

    def test_authenticated_access_scope(self):
        request = self.factory.get('/')
        request.user = UserFactory(vouched=False)
        eq_(UserAccessLevel.get_privacy(request), 'authenticated')

    def test_vouched_access_scope(self):
        request = self.factory.get('/')
        request.user = UserFactory(vouched=True)
        eq_(UserAccessLevel.get_privacy(request), 'vouched')

    def test_private_access_scope(self):
        request = self.factory.get('/')
        request.user = UserFactory()
        user = request.user
        eq_(UserAccessLevel.get_privacy(request, user), 'private')

    def test_private_access_scope_superuser(self):
        request = self.factory.get('/')
        request.user = UserFactory(is_superuser=True)
        user = request.user
        eq_(UserAccessLevel.get_privacy(request, user), 'private')

    def test_nda_access_scope(self):
        request = self.factory.get('/')
        user = UserFactory.create(vouched=True)
        request.user = user
        nda = GroupFactory.create(name='nda')
        GroupMembership.objects.create(userprofile=user.userprofile, group=nda,
                                       status=GroupMembership.MEMBER)
        eq_(UserAccessLevel.get_privacy(request), 'nda')

    def test_staff_access_scope(self):
        request = self.factory.get('/')
        user = UserFactory.create()
        user.userprofile.is_staff = True
        user.userprofile.save()
        request.user = user
        eq_(UserAccessLevel.get_privacy(request), 'staff')
