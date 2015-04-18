from django.forms import ValidationError

from nose.tools import eq_

from mozillians.common.tests import TestCase
from mozillians.users.admin import UserProfileAdminForm
from mozillians.users.tests import UserFactory


class UserProfileAdminFormTests(TestCase):

    def test_clean_username_same(self):
        user = UserFactory.create(username='foo')
        form = UserProfileAdminForm(None, instance=user.userprofile)
        form.cleaned_data = {'username': 'foo'}
        eq_(form.clean_username(), 'foo')

    def test_clean_username_new_valid(self):
        user = UserFactory.create(username='foo')
        form = UserProfileAdminForm(None, instance=user.userprofile)
        form.cleaned_data = {'username': 'bar'}
        eq_(form.clean_username(), 'bar')

    def test_clean_username_invalid(self):
        UserFactory.create(username='bar')
        user = UserFactory.create(username='foo')
        form = UserProfileAdminForm(None, instance=user.userprofile)
        form.cleaned_data = {'username': 'bar'}
        with self.assertRaises(ValidationError):
            form.clean_username()

    def test_clean_email_same(self):
        user = UserFactory.create(email='foo@example.com')
        form = UserProfileAdminForm(None, instance=user.userprofile)
        form.cleaned_data = {'email': 'foo@example.com'}
        eq_(form.clean_email(), 'foo@example.com')

    def test_clean_email_new_valid(self):
        user = UserFactory.create(email='foo@example.com')
        form = UserProfileAdminForm(None, instance=user.userprofile)
        form.cleaned_data = {'email': 'bar@example.com'}
        eq_(form.clean_email(), 'bar@example.com')

    def test_clean_email_invalid(self):
        UserFactory.create(email='bar@example.com')
        user = UserFactory.create(email='foo@example.com')
        form = UserProfileAdminForm(None, instance=user.userprofile)
        form.cleaned_data = {'email': 'bar@example.com'}
        with self.assertRaises(ValidationError):
            form.clean_email()
