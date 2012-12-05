import json

from django.contrib.auth.models import User
from django.test.utils import override_settings

from elasticutils.contrib.django import get_es
from funfactory.helpers import urlparams
from funfactory.urlresolvers import reverse
from mock import patch
from nose.tools import eq_, nottest
from product_details import product_details
from pyquery import PyQuery as pq

from apps.api.models import APIApp
from common import browserid_mock
from common.tests import ESTestCase, user
from groups.models import Group, Language, Skill

from .cron import index_all_profiles
from .helpers import validate_username
from .models import UserProfile, UsernameBlacklist

Group.objects.get_or_create(name='staff', system=True)
COUNTRIES = product_details.get_regions('en-US')


class RegistrationTest(ESTestCase):
    """Tests registration."""
    # Assertion doesn't matter since we monkey patched it for testing
    fake_assertion = 'mrfusionsomereallylongstring'

    def test_validate_username(self):
        """Test validate_username helper."""
        valid_usernames = ['giorgos', 'aakash',
                           'nikos', 'bat-man']

        invalid_usernames = ['administrator', 'test',
                             'no-reply', 'noreply', 'spam']

        for name in valid_usernames:
            self.assertTrue(validate_username(name),
                            'Username: %s did not pass test' % name)

        for name in invalid_usernames:
            self.assertFalse(validate_username(name),
                            'Username: %s did not pass test' % name)

    def test_mozillacom_registration(self):
        """Verify @mozilla.com users are auto-vouched and marked "staff"."""

        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid('mrfusion@mozilla.com'):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        d = dict(username='ad',
                 email='mrfusion@mozilla.com',
                 full_name='Akaaaaaaash Desaaaaaaai',
                 optin=True)
        with browserid_mock.mock_browserid('mrfusion@mozilla.com'):
            r = self.client.post(reverse('register'), d, follow=True)

        doc = pq(r.content)

        assert r.context['user'].get_profile().is_vouched, (
                "Moz.com should be auto-vouched")

        assert not doc('#pending-approval'), (
                'Moz.com profile page should not having pending vouch div.')

        assert r.context['user'].get_profile().groups.filter(name='staff'), (
                'Moz.com should belong to the "staff" group.')

    def test_plus_signs(self):
        email = 'mrfusion+dotcom@mozilla.com'
        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        d = dict(username='ad',
                 email=email,
                 full_name='Akaaaaaaash Desaaaaaaai',
                 optin=True)
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('register'), d, follow=True)

        assert User.objects.filter(email=d['email'])

    def test_username(self):
        """Test that we can submit a perfectly cromulent username.

        We verify that /:username then works as well.

        """
        email = 'mrfusion+dotcom@mozilla.com'
        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)
        d = dict(email=email,
                 username='mrfusion',
                 full_name='Akaaaaaaash Desaaaaaaai',
                 optin=True)
        with browserid_mock.mock_browserid(email):
            r = self.client.post(reverse('register'), d)
        eq_(r.status_code, 302, "Problems if we didn't redirect...")
        u = User.objects.filter(email=d['email'])[0]
        eq_(u.username, 'mrfusion', "Username didn't get set.")

        r = self.mozillian_client.get(reverse('profile', args=['mrfusion']),
                                              follow=True)
        eq_(r.status_code, 200)
        eq_(r.context['profile'].user_id, u.id)

    def test_username_characters(self):
        """Verify usernames can have digits/symbols, but nothing too
        insane.

        """
        email = 'mrfusion+dotcom@mozilla.com'
        username = 'mr.fu+s_i-on@246'
        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        d = dict(email=email,
                 username=username,
                 full_name='Akaaaaaaash Desaaaaaaai',
                 optin=True)
        with browserid_mock.mock_browserid(email):
            r = self.client.post(reverse('register'), d)
        eq_(r.status_code, 302, (
                'Registration flow should finish with a redirect.'))
        u = User.objects.get(email=d['email'])
        eq_(u.username, username, 'Username should be set to "%s".' % username)

        r = self.mozillian_client.get(reverse('profile', args=[username]),
                                              follow=True)
        eq_(r.status_code, 200)
        eq_(r.context['profile'].user_id, u.id)

        # Now test a username with even weirder characters that we don't allow.
        bad_user_email = 'mrfusion+coolbeans@mozilla.com'
        bad_username = 'mr.we*rd'
        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        d = dict(email=bad_user_email,
                 username=bad_username,
                 full_name='Akaaaaaaash Desaaaaaaai',
                 optin=True)
        with browserid_mock.mock_browserid(email):
            r = self.client.post(reverse('register'), d)
        eq_(r.status_code, 302, (
                'Registration flow should fail; username is bad.'))
        assert not User.objects.filter(email=d['email']), (
                "User shouldn't exist; username was bad.")

    def test_bad_username(self):
        """'about' is a terrible username, as are its silly friends.

        Let's make some stop words *and* analyze the routing system,
        whenever someone sets their username and verify that they can't
        be 'about' or 'help' or anything that is in use.
        """
        email = 'mrfusion+dotcom@mozilla.com'
        badnames = UsernameBlacklist.objects.all().values_list('value',
                                                               flat=True)
        # BrowserID needs an assertion not to be whiney
        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        for name in badnames:
            d = dict(email=email,
                     username=name,
                     full_name='Akaaaaaaash Desaaaaaaai',
                     optin=True)
            with browserid_mock.mock_browserid(email):
                r = self.client.post(reverse('register'), d)

            eq_(r.status_code, 200,
                'This form should fail for "%s", and say so.' % name)
            assert r.context['user_form'].errors, (
                "Didn't raise errors for %s" % name)

    def test_nickname_changes_before_vouch(self):
        """Notify pre-vouched users of URL change from nickname
        changes.

        See: https://bugzilla.mozilla.org/show_bug.cgi?id=736556

        """
        d = dict(assertion=self.fake_assertion)
        email = 'soy@latte.net'
        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        # Note: No username supplied.
        d = dict(email=email,
                 full_name='Tofu Matt',
                 optin=True)
        with browserid_mock.mock_browserid(email):
            r = self.client.post(reverse('register'), d, follow=True)

        assert r.context['user'].id, 'User should be created'
        assert not r.context['user'].get_profile().is_vouched, (
                'User should not be vouched')

        d['username'] = 'foobar'
        r = self.client.post(reverse('profile.edit'), d, follow=True)
        assert 'You changed your username;' in r.content, (
                'User should know that changing their username changes '
                'their URL.')

    def test_repeat_username(self):
        """Verify one cannot repeat email adresses."""
        register = dict(username='repeatedun',
                        full_name='Akaaaaaaash Desaaaaaaai',
                        optin=True)

        # Create first user
        email1 = 'mRfUsIoN@mozilla.com'
        register.update(email=email1)
        d = dict(assertion=self.fake_assertion)
        with browserid_mock.mock_browserid(email1):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        with browserid_mock.mock_browserid(email1):
            self.client.post(reverse('register'), register, follow=True)

        self.client.logout()
        # Create a different user
        email2 = 'coldfusion@gmail.com'
        register.update(email=email2)
        with browserid_mock.mock_browserid(email2):
            self.client.post(reverse('browserid_verify'), d, follow=True)

        with browserid_mock.mock_browserid(email2):
            r = self.client.post(reverse('register'), register, follow=True)

        # Make sure we can't use the same username twice
        assert r.context['user_form'].errors, "Form should throw errors."


class TestThingsForPeople(ESTestCase):
    """Verify that the wrong users don't see things."""

    def test_searchbox(self):
        url = reverse('home')
        r = self.client.get(url)
        doc = pq(r.content)
        assert not doc('input[type=text]')
        r = self.pending_client.get(url)
        doc = pq(r.content)
        assert not doc('input[type=text]')
        r = self.mozillian_client.get(url)
        doc = pq(r.content)
        assert doc('input[type=text]')

    def test_invitelink(self):
        url = reverse('home')
        r = self.client.get(url)
        doc = pq(r.content)
        assert not doc('a#invite')
        r = self.pending_client.get(url)
        doc = pq(r.content)
        assert not doc('a#invite'), "Unvouched can't invite."
        r = self.mozillian_client.get(url)
        doc = pq(r.content)
        assert doc('a#invite')

    def test_register_redirects_for_authenticated_users(self):
        """Ensure only anonymous users can register an account."""
        r = self.client.get(reverse('home'))
        self.assertTrue(200 == r.status_code,
                        'Anonymous users can access the homepage to '
                        'begin registration flow')

        r = self.mozillian_client.get(reverse('register'))
        eq_(302, r.status_code,
            'Authenticated users are redirected from registration.')

    def test_vouchlink(self):
        """No vouch link when PENDING looks at PENDING."""
        url = reverse('profile', args=['pending'])
        r = self.mozillian_client.get(url)
        doc = pq(r.content)
        assert doc('#vouch-form button')
        r = self.pending_client.get(url)
        doc = pq(r.content)
        errmsg = 'Self vouching... silliness.'
        assert not doc('#vouch-form button'), errmsg
        assert 'Vouch for me' not in r.content, errmsg

    @patch('users.admin.index_all_profiles')
    def test_es_index_admin_view(self, mock_obj):
        """Test that admin:user_index_profiles work fires a re-index."""
        self.mozillian.is_superuser = True
        self.mozillian.is_staff = True
        self.mozillian.save()
        url = reverse('admin:users_index_profiles')
        self.client.login(email=self.mozillian.email)
        self.client.get(url)
        mock_obj.assert_any_call()


class VouchTest(ESTestCase):

    # TODO
    # Mark this as nottest until we decide the policy in search
    # page. Then fix accordingly.
    @nottest
    def test_vouch_method(self):
        """Test UserProfile.vouch()

        Assert that a previously unvouched user shows up as unvouched
        in the database.

        Assert that when vouched they are listed as vouched.
        """
        vouchee = self.mozillian.get_profile()
        profile = self.pending.get_profile()
        assert not profile.is_vouched, 'User should not yet be vouched.'
        r = self.mozillian_client.get(reverse('search'),
                                      {'q': self.pending.email})
        assert 'Non-Vouched' in r.content, (
                'User should not appear as a Mozillian in search.')

        profile.vouch(vouchee)
        profile = UserProfile.objects.get(pk=profile.pk)
        assert profile.is_vouched, 'User should be marked as vouched.'

        r = self.mozillian_client.get(reverse('profile', args=['pending']))
        eq_(r.status_code, 200)
        doc = pq(r.content)
        assert 'Mozillian Profile' in r.content, (
                'User should appear as having a vouched profile.')
        assert not 'Pending Profile' in r.content, (
                'User should not appear as having a pending profile.')
        assert not doc('#pending-approval'), (
                'Pending profile div should not be in DOM.')

        # Make sure the user appears vouched in search results
        r = self.mozillian_client.get(reverse('search'),
                                      {'q': self.pending.email})
        assert 'Mozillian' in r.content, (
                'User should appear as a Mozillian in search.')


class TestUser(ESTestCase):
    """Test User functionality."""

    def test_userprofile(self):
        u = user()

        UserProfile.objects.all().delete()

        # Somehow the User lacks a UserProfile
        # Note that u.get_profile() caches in memory.
        self.assertRaises(UserProfile.DoesNotExist,
                          lambda: u.userprofile)

        # Sign in
        with browserid_mock.mock_browserid(u.email):
            d = dict(assertion='qwer')
            self.client.post(reverse('browserid_verify'), d, follow=True)

        # Good to go
        assert u.get_profile()

    def test_blank_ircname(self):
        username = 'thisisatest'
        email = 'test@example.com'
        register = dict(username=username,
                        full_name='David Teststhings',
                        optin=True)
        d = {'assertion': 'rarrr'}

        with browserid_mock.mock_browserid(email):
            self.client.post(reverse('browserid_verify'), d, follow=True)
            self.client.post(reverse('register'), register, follow=True)

        u = User.objects.filter(email=email)[0]
        p = u.get_profile()
        p.ircname = ''
        eq_(p.ircname, '', 'We need to allow IRCname to be blank')


class TestMigrateRegistration(ESTestCase):
        """Test funky behavior of flee ldap."""
        email = 'robot1337@domain.com'

        def test_login(self):
            """Given an invite_url go to it and redeem an invite."""
            # Lettuce make sure we have a clean slate

            info = dict(full_name='Akaaaaaaash Desaaaaaaai', optin=True)
            self.client.logout()
            u = User.objects.create(username='robot1337', email=self.email)
            p = u.get_profile()

            p.full_name = info['full_name']
            u.save()
            p.save()

            # BrowserID needs an assertion not to be whiney
            d = dict(assertion='tofu')
            with browserid_mock.mock_browserid(self.email):
                r = self.client.post(reverse('browserid_verify'),
                                     d, follow=True)

            eq_(r.status_code, 200)

            # Now let's register
            with browserid_mock.mock_browserid(self.email):
                r = self.client.post(reverse('register'), info, follow=True)

            eq_(r.status_code, 200)


@override_settings(AUTO_VOUCH_DOMAINS=['mozilla.com'])
class AutoVouchTests(ESTestCase):

    def test_only_autovouch_in_staff(self):
        """Restrict the staff group to emails in AUTO_VOUCH_DOMAINS."""
        staff = Group.objects.get_or_create(name='staff', system=True)[0]
        staff_user = user(email='abcd@mozilla.com')
        staff_profile = staff_user.get_profile()
        staff_profile.save()
        assert staff in staff_profile.groups.all(), (
            'Auto-vouched email in staff group by default.')

        staff_profile.groups.remove(staff)
        staff_profile.save()
        assert staff in staff_profile.groups.all(), (
            'Auto-vouched email cannot be removed from staff group.')

        community_user = user()
        community_profile = community_user.get_profile()
        community_profile.save()
        assert staff not in community_profile.groups.all(), (
            'Non-auto-vouched email not automatically in staff group.')

        community_profile.groups.add(staff)
        community_profile.save()
        assert staff not in community_profile.groups.all(), (
            'Non-auto-vouched email cannot be added to staff group.')

    def test_autovouch_email(self):
        """Users with emails in AUTO_VOUCH_DOMAINS should be vouched."""
        auto_user = user(email='abcd@mozilla.com')
        auto_profile = auto_user.get_profile()
        auto_profile.save()
        assert auto_profile.is_vouched, 'Profile should be vouched.'
        assert auto_profile.vouched_by is None, (
            'Profile should not have a voucher.')

        non_auto_user = user()
        non_auto_profile = non_auto_user.get_profile()
        non_auto_profile.save()
        assert not non_auto_profile.is_vouched, (
            'Profile should not be vouched.')


@override_settings(
    AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.ModelBackend'])
class UsernameRedirectionMiddlewareTests(ESTestCase):
    # Assertion doesn't matter since we monkey patched it for testing
    def test_username_redirection_middleware(self):
        """Test the username redirection middleware."""

        auto_user = user(username='lalala')
        self.client.login(username=auto_user.username, password='testpass')
        response = self.client.get('/%s' % auto_user.username, follow=True)
        self.assertTemplateUsed(response, 'phonebook/profile.html')

        response = self.client.get('/%s' % 'invaliduser', follow=True)
        self.assertTemplateUsed(response, '404.html')


class SearchTests(ESTestCase):

    def setUp(self):
        self.data = {'country': 'us',
                     'region': 'California',
                     'city': 'Mountain View',
                     'ircname': 'hax0r',
                     'bio': 'I love ice cream. I code. I tweet.',
                     'website': 'http://www.example.com',
                     'full_name': 'Nikos Koukos'}
        self.auto_user = user()
        self.up = self.auto_user.userprofile
        for key, value in self.data.iteritems():
            setattr(self.up, key, value)
        self.up.save()

    def test_search_generic(self):
        for key, value in self.data.iteritems():
            if key == 'country':
                value = COUNTRIES[value]
            results = UserProfile.search(value)
            self.assertEqual(len(results), 1)

        results = UserProfile.search(self.up.full_name)
        self.assertEqual(len(results), 1)

        results = UserProfile.search('mountain')
        self.assertEqual(len(results), 0)

        results = UserProfile.search(self.up.full_name[:2])
        self.assertEqual(len(results), 1)

        results = UserProfile.search(
            self.up.bio.split(' ')[3])
        self.assertEqual(len(results), 1)


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
        for name in [self.auto_user.userprofile.full_name,
                     self.auto_user.userprofile.full_name.split(' ')[0],
                     self.auto_user.userprofile.full_name.split(' ')[1]]:
            new_url = urlparams(url, app_name=self.app.name,
                                app_key=self.app.key, name=name)
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
