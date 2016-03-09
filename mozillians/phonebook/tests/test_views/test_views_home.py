from django.core.urlresolvers import reverse
from django.test import Client

from nose.tools import ok_

from mozillians.common.tests import TestCase
from mozillians.users.tests import UserFactory


class HomeTests(TestCase):
    def test_home_anonymous(self):
        client = Client()
        response = client.get(reverse('phonebook:home'), follow=True)
        self.assertJinja2TemplateUsed(response, 'phonebook/home.html')
        ok_('profile' not in response.context)

    def test_home_unvouched(self):
        user = UserFactory.create(vouched=False)
        with self.login(user) as client:
            response = client.get(reverse('phonebook:home'), follow=True)
        self.assertJinja2TemplateUsed(response, 'phonebook/home.html')

    def test_home_vouched(self):
        user = UserFactory.create()
        with self.login(user) as client:
            response = client.get(reverse('phonebook:home'), follow=True)
        self.assertJinja2TemplateUsed(response, 'phonebook/home.html')
