import json
import requests

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from mock import patch, Mock
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.dino_park.utils import (_dino_park_get_profile_by_userid, DinoErrorResponse,
                                        UserAccessLevel)
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


class TestErrorResponses(TestCase):
    """Tests for DinoPark response codes."""

    def test_permission_error(self):
        resp = DinoErrorResponse.get_error(DinoErrorResponse.PERMISSION_ERROR)
        eq_(resp.status_code, 403)
        eq_(json.loads(resp.content)['error'], u'Permission Denied: Scope mismatch.')

    def test_attribute_error(self):
        resp = DinoErrorResponse.get_error(DinoErrorResponse.ATTRIBUTE_ERROR,
                                           status_code=503,
                                           attribute='foo')
        eq_(resp.status_code, 503)
        eq_(json.loads(resp.content)['error'], u'Attribute foo is not valid.')

    def test_default_status_code(self):
        resp = DinoErrorResponse.get_error(DinoErrorResponse.PERMISSION_ERROR)
        eq_(resp.status_code, 403)


class TestGetProfileByUserID(TestCase):
    """Tests for the utility helper that fetches profiles by Auth0 user ID."""

    def test_no_user_id(self):
        ok_(not _dino_park_get_profile_by_userid(user_id=''))

    @patch('mozillians.dino_park.utils.requests.get')
    def test_bad_status_code(self, request_mock):
        mock_response = Mock()
        exception_error = requests.exceptions.HTTPError()
        mock_response.raise_for_status.side_effect = exception_error

        request_mock.return_value = mock_response
        request_mock.return_value.status_code = 503
        ok_(not _dino_park_get_profile_by_userid(user_id='dinos'))

    @patch('mozillians.dino_park.utils.requests.get')
    def test_return_username(self, request_mock):
        mock_response = Mock()
        mock_response.json.return_value = {
            "usernames": {
                "values":
                {
                    "mozilliansorg": 'DinoPark'
                }
            },
            "foo": "bar"
        }
        request_mock.return_value = mock_response
        eq_(_dino_park_get_profile_by_userid(user_id='dinos', return_username=True), 'DinoPark')

    @patch('mozillians.dino_park.utils.requests.get')
    def test_get_profile(self, request_mock):
        mock_response = Mock()
        profile = {
            "usernames": {
                "values":
                {
                    "mozilliansorg": 'DinoPark'
                }
            },
            "foo": "bar"
        }
        mock_response.json.return_value = profile
        request_mock.return_value = mock_response
        eq_(_dino_park_get_profile_by_userid(user_id='dinos'), profile)
