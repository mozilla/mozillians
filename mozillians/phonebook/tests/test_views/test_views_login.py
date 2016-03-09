from django.core.urlresolvers import reverse
from django.test import Client

from mozillians.common.tests import TestCase, requires_login
from mozillians.users.tests import UserFactory


class LoginTests(TestCase):

    @requires_login()
    def test_login_anonymous(self):
        client = Client()
        client.get(reverse('phonebook:login'), follow=True)

    def test_login_unvouched(self):
        user = UserFactory.create(vouched=False)
        with self.login(user) as client:
            response = client.get(reverse('phonebook:login'), follow=True)
        self.assertJinja2TemplateUsed(response, 'phonebook/home.html')

    def test_login_vouched(self):
        user = UserFactory.create()
        with self.login(user) as client:
            response = client.get(reverse('phonebook:login'), follow=True)
        self.assertJinja2TemplateUsed(response, 'phonebook/home.html')

    def test_login_incomplete_profile(self):
        user = UserFactory.create(userprofile={'full_name': ''})
        with self.login(user) as client:
            response = client.get(reverse('phonebook:login'), follow=True)
        self.assertJinja2TemplateUsed(response, 'phonebook/edit_profile.html')
