from mock import patch
from nose.tools import eq_

from mozillians.common.tests import TestCase
from mozillians.users.managers import PUBLIC
from mozillians.users.models import UserProfile
from mozillians.users.tests import UserFactory


class UserProfileQuerySetTests(TestCase):
    def test_privacy_level(self):
        queryset = UserProfile.objects.all().privacy_level(99)
        eq_(queryset._privacy_level, 99)

    @patch('mozillians.users.models.UserProfile.privacy_fields')
    def test_public(self, mock_privacy_fields):
        mock_privacy_fields.return_value = {'full_name': '', 'email': ''}
        UserFactory.create()
        UserFactory.create(userprofile={'is_vouched': True})
        public_user_1 = UserFactory.create(
            userprofile={'is_vouched': True, 'privacy_full_name': PUBLIC})
        public_user_2 = UserFactory.create(
            userprofile={'is_vouched': True, 'privacy_email': PUBLIC})
        queryset = UserProfile.objects.public()
        eq_(queryset.count(), 2)
        eq_(set(queryset.all()), set([public_user_1.userprofile,
                                      public_user_2.userprofile]))

    def test_vouched(self):
        vouched_user = UserFactory.create(userprofile={'is_vouched': True})
        UserFactory.create()
        UserFactory.create(userprofile={'is_vouched': True, 'full_name': ''})
        queryset = UserProfile.objects.vouched()
        eq_(queryset.count(), 1)
        eq_(queryset[0], vouched_user.userprofile)

    def test_complete(self):
        complete_user_1 = UserFactory.create()
        complete_user_2 = UserFactory.create(userprofile={'is_vouched': True})
        UserFactory.create(userprofile={'full_name': ''})
        UserFactory.create(userprofile={'is_vouched': True, 'full_name': ''})
        queryset = UserProfile.objects.complete()
        eq_(queryset.count(), 2)
        eq_(set(queryset.all()), set([complete_user_1.userprofile,
                                      complete_user_2.userprofile]))

    @patch('mozillians.users.managers.PUBLIC_INDEXABLE_FIELDS',
           {'full_name': '', 'email': ''})
    def test_public_indexable(self):
        public_indexable_user_1 = UserFactory.create(
            userprofile={'privacy_full_name': PUBLIC})
        public_indexable_user_2 = UserFactory.create(
            userprofile={'privacy_email': PUBLIC})
        UserFactory.create(userprofile={'privacy_email': PUBLIC, 'full_name': ''})
        UserFactory.create()
        queryset = UserProfile.objects.public_indexable()
        eq_(queryset.count(), 2)
        eq_(set(queryset.all()), set([public_indexable_user_1.userprofile,
                                      public_indexable_user_2.userprofile]))

    def test_not_public_indexable(self):
        UserFactory.create(userprofile={'privacy_full_name': PUBLIC})
        UserFactory.create(userprofile={'privacy_email': PUBLIC})
        UserFactory.create(userprofile={'privacy_email': PUBLIC, 'full_name': ''})
        notpublic_user_1 = UserFactory.create()
        queryset = UserProfile.objects.not_public_indexable()
        eq_(queryset.count(), 1)
        eq_(queryset[0], notpublic_user_1.userprofile)

    def test_clone(self):
        queryset = UserProfile.objects.all()
        queryset.privacy_level(99)
        new_queryset = queryset.public()
        eq_(new_queryset._privacy_level, 99)

    def test_iterator(self):
        UserFactory.create()
        queryset = UserProfile.objects.all()
        queryset.privacy_level(99)
        eq_(queryset.all()[0]._privacy_level, 99)
