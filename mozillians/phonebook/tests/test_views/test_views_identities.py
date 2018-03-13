from django.core.urlresolvers import reverse
from django.test.utils import override_script_prefix

from mock import ANY, patch
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.users.models import IdpProfile
from mozillians.users.tests import UserFactory


class IdentitiesViewsTests(TestCase):

    def test_view_identities(self):
        user = UserFactory.create()
        IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='email|',
            email=user.email,
            primary=True
        )

        with self.login(user) as client:
            url = reverse('phonebook:profile_edit')
            response = client.get(url, follow=True)

        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/edit_profile.html')

    def test_delete_identity_of_different_user(self):
        user = UserFactory.create()
        email_owner = UserFactory.create()
        idp = IdpProfile.objects.create(
            profile=email_owner.userprofile,
            auth0_user_id='email|',
            email=email_owner.email,
            primary=True
        )

        with self.login(user) as client:
            url = reverse('phonebook:delete_identity', kwargs={'identity_pk': idp.pk})
            response = client.get(url, follow=True)

        eq_(response.status_code, 404)

    @patch('mozillians.phonebook.views.messages')
    def test_delete_valid_identity(self, mocked_message):
        user = UserFactory.create()
        idp_primary = IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='github|1',
            email=user.email,
            primary=True
        )
        idp = IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='email|2',
            email=user.email,
            primary=False
        )

        with self.login(user) as client:
            url = reverse('phonebook:delete_identity', kwargs={'identity_pk': idp.pk})
            response = client.get(url, follow=True)

        ok_(not IdpProfile.objects.filter(pk=idp.pk).exists())
        ok_(IdpProfile.objects.filter(pk=idp_primary.pk).exists())
        with override_script_prefix('/en-US/'):
            url = reverse('phonebook:profile_edit')
        self.assertRedirects(response, url, status_code=301)
        msg = 'Identity {0} successfully deleted.'.format(idp.get_type_display())
        mocked_message.success.assert_called_once_with(ANY, msg)

    @patch('mozillians.phonebook.views.messages')
    def test_delete_primary_login_identity(self, mocked_message):
        user = UserFactory.create()
        idp = IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='email|',
            email=user.email,
            primary=True
        )

        with self.login(user) as client:
            url = reverse('phonebook:delete_identity', kwargs={'identity_pk': idp.pk})
            response = client.get(url, follow=True)

        ok_(IdpProfile.objects.filter(pk=idp.pk).exists())
        with override_script_prefix('/en-US/'):
            url = reverse('phonebook:profile_edit')
        self.assertRedirects(response, url, status_code=301)
        msg = 'Sorry the requested Identity cannot be deleted.'
        mocked_message.error.assert_called_once_with(ANY, msg)

    def test_change_identity_of_another_user(self):
        user = UserFactory.create()
        email_owner = UserFactory.create()
        idp = IdpProfile.objects.create(
            profile=email_owner.userprofile,
            auth0_user_id='email|',
            email=email_owner.email,
            primary=True
        )

        with self.login(user) as client:
            url = reverse('phonebook:change_primary_contact_identity',
                          kwargs={'identity_pk': idp.pk})
            response = client.get(url, follow=True)

        eq_(response.status_code, 404)

    @patch('mozillians.phonebook.views.messages')
    def test_delete_primary_contact_identity(self, mocked_message):
        user = UserFactory.create()
        idp = IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='email|',
            email=user.email,
            primary=False,
            primary_contact_identity=True
        )

        with self.login(user) as client:
            url = reverse('phonebook:delete_identity', kwargs={'identity_pk': idp.pk})
            response = client.get(url, follow=True)

        ok_(IdpProfile.objects.filter(pk=idp.pk).exists())
        with override_script_prefix('/en-US/'):
            url = reverse('phonebook:profile_edit')
        self.assertRedirects(response, url, status_code=301)
        msg = 'Sorry the requested Identity cannot be deleted.'
        mocked_message.error.assert_called_once_with(ANY, msg)

    @patch('mozillians.phonebook.views.messages')
    def test_change_valid_identity(self, mocked_message):
        user = UserFactory.create()
        idp_primary = IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='github|1',
            email=user.email,
            primary=True
        )
        idp = IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='email|2',
            email=user.email,
            primary=False
        )
        ok_(IdpProfile.objects.filter(pk=idp_primary.pk, primary_contact_identity=True).exists())

        with self.login(user) as client:
            url = reverse('phonebook:change_primary_contact_identity',
                          kwargs={'identity_pk': idp.pk})
            response = client.get(url, follow=True)

        with override_script_prefix('/en-US/'):
            url = reverse('phonebook:profile_edit')
        self.assertRedirects(response, url, status_code=301)
        ok_(IdpProfile.objects.filter(pk=idp_primary.pk, primary_contact_identity=False).exists())
        ok_(IdpProfile.objects.filter(pk=idp.pk, primary_contact_identity=True).exists())
        msg = 'Primary Contact Identity successfully updated.'
        mocked_message.success.assert_called_once_with(ANY, msg)
