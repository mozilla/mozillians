from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.users.models import ExternalAccount
from mozillians.users.tests import UserFactory


class EditEmailsTests(TestCase):
    def test_view_emails(self):
        user = UserFactory.create()

        with self.login(user) as client:
            url = reverse('phonebook:profile_edit')
            response = client.get(url, follow=True)

        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/edit_profile.html')

    def test_delete_email_invalid(self):
        user = UserFactory.create()
        email_owner = UserFactory.create()
        kwargs = {'type': ExternalAccount.TYPE_EMAIL, 'identifier': 'foo@example.com'}
        email = email_owner.userprofile.externalaccount_set.create(**kwargs)

        with self.login(user) as client:
            url = reverse('phonebook:delete_email', kwargs={'email_pk': email.pk})
            response = client.get(url, follow=True)

        eq_(response.status_code, 404)

    def test_delete_email_valid(self):
        user = UserFactory.create()
        kwargs = {'type': ExternalAccount.TYPE_EMAIL, 'identifier': 'foo@example.com'}
        email = user.userprofile.externalaccount_set.create(**kwargs)

        with self.login(user) as client:
            url = reverse('phonebook:delete_email', kwargs={'email_pk': email.pk})
            response = client.get(url, follow=True)

        ok_(not ExternalAccount.objects.filter(pk=email.pk).exists())
        url = reverse('phonebook:profile_edit', prefix='/en-US/')
        self.assertRedirects(response, url, status_code=301)

    def test_change_primary_email_invalid(self):
        user = UserFactory.create()
        email_owner = UserFactory.create()
        kwargs = {'type': ExternalAccount.TYPE_EMAIL, 'identifier': 'foo@example.com'}
        email = email_owner.userprofile.externalaccount_set.create(**kwargs)

        with self.login(user) as client:
            url = reverse('phonebook:change_primary_email', kwargs={'email_pk': email.pk})
            response = client.get(url, follow=True)

        eq_(response.status_code, 404)

    def test_change_primary_email_valid(self):
        user = UserFactory.create(email='foo@example.com')
        kwargs = {'type': ExternalAccount.TYPE_EMAIL, 'identifier': 'bar@example.com'}
        email = user.userprofile.externalaccount_set.create(**kwargs)

        ok_(not user.userprofile.externalaccount_set.filter(identifier='foo@example.com').exists())

        with self.login(user) as client:
            url = reverse('phonebook:change_primary_email', kwargs={'email_pk': email.pk})
            response = client.get(url, follow=True)

        url = reverse('phonebook:profile_edit', prefix='/en-US/')
        self.assertRedirects(response, url, status_code=301)

        user = User.objects.get(pk=user.pk)
        eq_(user.email, 'bar@example.com')
        ok_(not user.userprofile.externalaccount_set.filter(identifier='bar@example.com').exists())
        ok_(user.userprofile.externalaccount_set.filter(identifier='foo@example.com').exists())
