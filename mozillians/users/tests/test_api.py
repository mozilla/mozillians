import json

from django.test.utils import override_settings

from elasticutils.contrib.django import get_es
from funfactory.helpers import urlparams
from funfactory.urlresolvers import reverse
from product_details import product_details

from mozillians.api.models import APIApp
from mozillians.common.tests.init import ESTestCase, user
from mozillians.groups.models import Group, Language, Skill
from mozillians.users.cron import index_all_profiles


COUNTRIES = product_details.get_regions('en-US')


class APITests(ESTestCase):
    """API Tests."""

    def setUp(self):
        """Setup API Testing."""
        # create an APP
        self.auto_user = user()
        up = self.auto_user.userprofile
        up.set_membership(Group, 'nice guy')
        up.set_membership(Skill, 'python')
        up.set_membership(Language, 'Greek')
        up.ircname = 'foobar'
        up.country = 'gr'
        up.region = 'Attika'
        up.city = 'Athens'
        up.full_name = 'Foo Bar'
        up.save()

        self.app = APIApp.objects.create(name='test_app',
                                         description='Foo',
                                         owner=self.mozillian,
                                         is_mozilla_app=False,
                                         is_active=False)

        index_all_profiles()
        get_es().flush(refresh=True)

    def test_get_users(self):
        """Test permissions of API dispatch list of 'users' resource."""
        # No app
        url = reverse('api_dispatch_list', kwargs={'api_name': 'v1',
                                                   'resource_name': 'users'})
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 401,
                         'Unauthorized call gets results.')

        # Invalid app
        new_url = urlparams(url, app_name='invalid', app_key='xxx')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 401,
                         'Invalid App call gets results.')

        # Inactive app
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key)
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 401,
                         'Inactive App call gets results.')

        # Valid community app with filtering
        self.app.is_active = True
        self.app.save()
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            email=self.mozillian.email)
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200,
                         'Community App w/ filtering does not get results.')

        # Valid community app with filtering, email capitalized
        self.app.is_active = True
        self.app.save()
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            email=self.auto_user.email.capitalize())
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200,
                         ('Community App w/ filtering does not '
                          'get results with capitalized email.'))

        # Valid community app without filtering
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key)
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 403,
                         'Community App w/o filters does get results.')

        # Valid Mozilla app with filtering
        self.app.is_mozilla_app = True
        self.app.save()
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            email=self.mozillian.email)
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200,
                         'Mozilla App w/ filtering does not get results.')

        # Valid Mozilla app without filtering
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key)
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200,
                         'Mozilla App w/o filtering does not get results.')

    def test_api_search_ircname(self):
        """Test API search ircname."""
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()
        url = reverse('api_dispatch_list', kwargs={'api_name': 'v1',
                                                   'resource_name': 'users'})

        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            ircname=self.auto_user.userprofile.ircname)
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['total_count'], 1)

        # Search nonexistent term
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            ircname='random')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['total_count'], 0)

    def test_api_search_country(self):
        """Test API search country."""
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()
        url = reverse('api_dispatch_list', kwargs={'api_name': 'v1',
                                                   'resource_name': 'users'})

        country=COUNTRIES[self.auto_user.userprofile.country]
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            country=country)
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['total_count'], 1)

        # Search nonexistent term
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            country='random')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['total_count'], 0)

    def test_api_search_region(self):
        """Test API search region."""
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()
        url = reverse('api_dispatch_list', kwargs={'api_name': 'v1',
                                                   'resource_name': 'users'})

        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            region=self.auto_user.userprofile.region)
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['total_count'], 1)

        # Search nonexistent term
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            region='random')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['total_count'], 0)

    def test_api_search_city(self):
        """Test API search city."""
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()
        url = reverse('api_dispatch_list', kwargs={'api_name': 'v1',
                                                   'resource_name': 'users'})

        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            city=self.auto_user.userprofile.city)
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['total_count'], 1)

        # Search nonexistent term
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            city='random')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['total_count'], 0)

    def test_api_search_name(self):
        """Test API search name."""
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()
        url = reverse('api_dispatch_list', kwargs={'api_name': 'v1',
                                                   'resource_name': 'users'})

        # Search name using
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            name=self.auto_user.userprofile.full_name)
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['meta']['total_count'], 1)

        # Search nonexistent term
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            name='random')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['total_count'], 0)

    def test_api_search_groups(self):
        """Test API search groups."""
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()
        url = reverse('api_dispatch_list', kwargs={'api_name': 'v1',
                                                   'resource_name': 'users'})

        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            groups=self.auto_user.userprofile.groups.all()[0])
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['total_count'], 1)

        # Search nonexistent term
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            groups='random')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['total_count'], 0)

    def test_api_search_skills(self):
        """Test API search skills."""
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()
        url = reverse('api_dispatch_list', kwargs={'api_name': 'v1',
                                                   'resource_name': 'users'})

        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            skills=self.auto_user.userprofile.skills.all()[0])
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['total_count'], 1)

        # Search nonexistent term
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            skills='random')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['total_count'], 0)

    def test_api_search_languages(self):
        """Test API search languages."""
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()
        url = reverse('api_dispatch_list', kwargs={'api_name': 'v1',
                                                   'resource_name': 'users'})

        new_url = urlparams(
            url, app_name=self.app.name, app_key=self.app.key,
            languages=self.auto_user.userprofile.languages.all()[0])
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['total_count'], 1)

        # Search nonexistent term
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            languages='random')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['total_count'], 0)

    def test_valid_app(self):
        """Test valid app access."""
        url = reverse('api_dispatch_list', kwargs={'api_name': 'v1',
                                                   'resource_name': 'users'})
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key)
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

    def test_invalid_app_key(self):
        """Test invalid app key access."""
        url = reverse('api_dispatch_list', kwargs={'api_name': 'v1',
                                                   'resource_name': 'users'})
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()
        new_url = urlparams(url, app_name=self.app.name, app_key='random')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 401)

    def test_invalid_app_name(self):
        """Test invalid app name access."""
        url = reverse('api_dispatch_list', kwargs={'api_name': 'v1',
                                                   'resource_name': 'users'})
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()
        new_url = urlparams(url, app_name='random', app_key=self.app.key)
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 401)

    def test_huge_offset(self):
        """Test sending huge offset."""
        url = reverse('api_dispatch_list', kwargs={'api_name': 'v1',
                                                   'resource_name': 'users'})
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()

        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            offset=2000000000000000000000000000)
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['offset'], data['meta']['total_count'])

    @override_settings(HARD_API_LIMIT_PER_PAGE=50)
    def test_huge_limit(self):
        """Test sending huge limit."""
        url = reverse('api_dispatch_list', kwargs={'api_name': 'v1',
                                                   'resource_name': 'users'})
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()

        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            limit=20000)
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(data['meta']['limit'], 50)

    def test_inactive_app(self):
        """Test inactive app access."""
        url = reverse('api_dispatch_list', kwargs={'api_name': 'v1',
                                                   'resource_name': 'users'})
        self.app.is_mozilla_app = True
        self.app.is_active = False
        self.app.save()
        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key)
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 401)

    def test_api_permissions(self):
        """Test API permissions."""
        url = reverse('api_dispatch_list', kwargs={'api_name': 'v1',
                                                   'resource_name': 'users'})

        # Valid Mozilla app / User allows all to see he's vouched
        # status / User allows mozilla to access all his data
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()

        self.mozillian.userprofile.allows_mozilla_sites = True
        self.mozillian.userprofile.allows_community_sites = True
        self.mozillian.userprofile.save()

        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            email='u000001@mozillians.org')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertGreater(len(data['objects'][0]), 2)

        # Valid Mozilla app / User allows mozilla only to see he's vouched
        # status / User allows mozilla to access all his data
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()

        self.mozillian.userprofile.allows_mozilla_sites = True
        self.mozillian.userprofile.allows_community_sites = False
        self.mozillian.userprofile.save()

        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            email='u000001@mozillians.org')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertGreater(len(data['objects'][0]), 2)


        # Valid Mozilla app / User allows all to see he's vouched
        # status / User does not allow mozilla to access all his data
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()

        self.mozillian.userprofile.allows_mozilla_sites = False
        self.mozillian.userprofile.allows_community_sites = True
        self.mozillian.userprofile.save()

        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            email='u000001@mozillians.org')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['objects'][0]), 2)

        # Valid Mozilla app / User allows mozilla only to see he's vouched
        # status / User does not allow mozilla to access all his data
        self.app.is_mozilla_app = True
        self.app.is_active = True
        self.app.save()

        self.mozillian.userprofile.allows_mozilla_sites = False
        self.mozillian.userprofile.allows_community_sites = False
        self.mozillian.userprofile.save()

        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            email='u000001@mozillians.org')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['objects'][0]), 2)

        # Valid Community app / User allows all to see he's vouched
        # status / User allows mozilla to access all his data
        self.app.is_mozilla_app = False
        self.app.is_active = True
        self.app.save()

        self.mozillian.userprofile.allows_mozilla_sites = True
        self.mozillian.userprofile.allows_community_sites = True
        self.mozillian.userprofile.save()

        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            email='u000001@mozillians.org')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['objects']), 1)
        self.assertEqual(len(data['objects'][0]), 2)


        # Valid Community app / User allows mozilla only to see he's vouched
        # status / User allows mozilla to access all his data
        self.app.is_mozilla_app = False
        self.app.is_active = True
        self.app.save()

        self.mozillian.userprofile.allows_mozilla_sites = True
        self.mozillian.userprofile.allows_community_sites = False
        self.mozillian.userprofile.save()

        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            email='u000001@mozillians.org')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['objects']), 0)

        # Valid Community app / User allows all to see he's vouched
        # status / User does not allow mozilla to access all his data
        self.app.is_mozilla_app = False
        self.app.is_active = True
        self.app.save()

        self.mozillian.userprofile.allows_community_sites = True
        self.mozillian.userprofile.allows_mozilla_sites = False
        self.mozillian.userprofile.save()

        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            email='u000001@mozillians.org')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['objects'][0]), 2)

        # Valid Community app / User allows mozilla only to see he's vouched
        # status / User does not allow mozilla to access all his data
        self.app.is_mozilla_app = False
        self.app.is_active = True
        self.app.save()

        self.mozillian.userprofile.allows_community_sites = False
        self.mozillian.userprofile.allows_mozilla_sites = False
        self.mozillian.userprofile.save()

        new_url = urlparams(url, app_name=self.app.name, app_key=self.app.key,
                            email='u000001@mozillians.org')
        response = self.client.get(new_url, follow=True)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data['objects']), 0)
