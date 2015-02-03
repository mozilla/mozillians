from mock import patch
from nose.tools import eq_
from django.test import Client
from django.core.urlresolvers import reverse

from mozillians.users.tests import UserFactory, LanguageFactory
from mozillians.common.tests import TestCase, requires_login, requires_vouch


class ListLanguageTests(TestCase):

    @requires_login()
    def test_list_mozillians_by_language(self):
        client = Client()
        url = reverse('phonebook:list_language', kwargs={'language': 'russian'})
        client.get(url, follow=True)

    @requires_vouch()
    def test_list_mozilians_by_language_unvouched(self):
        user = UserFactory.create(vouched=False)
        with self.login(user) as client:
            url = reverse('phonebook:list_language', kwargs={'language': 'greek'})
            client.get(url, follow=True)

    @patch('mozillians.groups.views.settings.ITEMS_PER_PAGE', 1)
    def test_list_mozillians_by_language_vouched(self):
        user1 = UserFactory.create()
        lang = LanguageFactory.create(userprofile=user1.userprofile)
        lang.code = 'ru'
        lang.save()
        url = reverse('phonebook:list_language', kwargs={'language': 'russian'})
        user = UserFactory.create()
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        self.assertTemplateUsed(response, 'phonebook/language_list.html')
        eq_(response.context['people'].paginator.count, 1)
        eq_(response.context['people'].paginator.num_pages, 1)
        eq_(response.context['people'].number, 1)
        eq_(response.context['people'].object_list[0], user1.userprofile)

    @patch('mozillians.groups.views.settings.ITEMS_PER_PAGE', 1)
    def test_list_mozillians_by_language_vouched_two_pages(self):
        user1 = UserFactory.create()
        lang1 = LanguageFactory.create(userprofile=user1.userprofile)
        lang1.code = 'ru'
        lang1.save()
        user2 = UserFactory.create()
        lang2 = LanguageFactory.create(userprofile=user2.userprofile)
        lang2.code = 'ru'
        lang2.save()
        url = reverse('phonebook:list_language', kwargs={'language': 'russian'})
        user = UserFactory.create()
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.context['people'].paginator.count, 2)
        eq_(response.context['people'].paginator.num_pages, 2)
        eq_(response.context['people'].number, 1)

    @patch('mozillians.groups.views.settings.ITEMS_PER_PAGE', 1)
    def test_list_mozillians_by_language_vouched_empty_page(self):
        user1 = UserFactory.create()
        language = LanguageFactory.create(userprofile=user1.userprofile)
        language.code = 'el'
        language.save()
        user = UserFactory.create()
        url = reverse('phonebook:list_language', kwargs={'language': 'russian'})
        with self.login(user) as client:
            response = client.get(url, follow=True)
        eq_(response.status_code, 200)
        eq_(len(response.context['people'].object_list), 0)
