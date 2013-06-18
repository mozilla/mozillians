import os
from uuid import uuid4

from django import test
from django.contrib.auth.models import User

from funfactory.urlresolvers import set_url_prefix, reverse
from nose.tools import eq_
from pyquery import PyQuery as pq

from apps.users.models import MOZILLIANS
from apps.common.tests.init import ESTestCase, user


class TestDeleteUser(ESTestCase):
    """Separate test class used to test account deletion flow.

    We create a separate class to delete a user because other tests
    depend on Mozillian users existing.
    """

    def test_confirm_delete(self):
        """Test the account deletion flow, including confirmation.

        A user should not be presented with a form/link that allows
        them to delete their account without a confirmation page. Once
        they access that page, they should be presented with a link to
        'go back' to their profile or to permanently delete their
        account.

        This test is abstracted away to a generic user deletion flow
        so we can test both non-vouched and vouched user's ability to
        delete their own profile.

        """

        for _user in [self.mozillian, self.pending]:
            self._delete_flow(_user)

        pass

    def _delete_flow(self, user):
        """Private method used to walk through account deletion flow."""
        self.client.login(email=user.email)
        user_id = User.objects.get(email=user.email).id

        r = self.client.get(reverse('profile.edit'))
        doc = pq(r.content)

        # Make sure there's a link to a confirm deletion page, and nothing
        # pointing directly to the delete URL.
        eq_(reverse('profile.delete_confirm'),
            doc('a.delete').attr('href'),
            'We see a link to a confirmation page.')
        self.assertFalse(any((reverse('profile.delete') in el.action)
                              for el in doc('#main form')),
            "We don't see a form posting to the account delete URL.")

        # Follow the link to the deletion confirmation page.
        r = self.client.get(doc('a.delete').attr('href'))

        # Test that we can go back (i.e. cancel account deletion).
        doc = pq(r.content)
        eq_(reverse('profile.edit'),
            doc('#cancel-action').attr('href'))

        # Test that account deletion works.
        delete_url = doc('#delete-action').closest('form').attr('action')
        r = self.client.post(delete_url, follow=True)
        eq_(200, r.status_code)
        self.assertFalse(_logged_in_html(r))

        # Make sure the user data isn't there anymore
        assert not User.objects.get(id=user_id).first_name
        assert not User.objects.get(id=user_id).userprofile.full_name
        assert not User.objects.get(id=user_id).email
        assert not User.objects.get(id=user_id).is_active


class TestViews(ESTestCase):

    def test_anonymous_home(self):
        r = self.client.get('/', follow=True)
        self.assertEquals(200, r.status_code)
        doc = pq(r.content)
        self.assertTrue(doc('#create_profile'), 'We see a link to login')
        self.assertFalse(_logged_in_html(r))

    def test_pending_home(self):
        self.client.login(email=self.pending.email)
        r = self.client.get('/', follow=True)
        self.assertEquals(200, r.status_code)
        self.assertTrue(_logged_in_html(r))
        doc = pq(r.content)
        profile = reverse('profile', args=[self.pending.username])
        eq_(profile, doc('a#profile').attr('href'),
            'We see a link to our profile')

    def test_mozillian_home(self):
        self.client.login(email=self.mozillian.email)
        r = self.client.get('/', follow=True)
        self.assertEquals(200, r.status_code)
        self.assertTrue(_logged_in_html(r))
        doc = pq(r.content)
        profile = reverse('profile', args=[self.mozillian.username])
        eq_(profile, doc('a#profile').attr('href'),
            'We see a link to our profile')

    def test_user_view_own_profile(self):
        """Test user requests own profile."""
        def _get_page(client, user):
            url = reverse('profile', args=[user.username])
            response = client.get(url)
            self.assertEqual(response.status_code, 200)
            eq_(response.context['profile'].user, user)
        _get_page(self.mozillian_client, self.mozillian)
        _get_page(self.mozillian2_client, self.mozillian2)
        _get_page(self.pending_client, self.pending)
        _get_page(self.incomplete_client, self.incomplete)

    def test_user_view_nonpublic_mozillian_profile(self):
        """Test user requests non public mozillian profile."""
        def _get_page(client, status_code):
            url = reverse('profile', args=[self.mozillian.username])
            response = client.get(url)
            eq_(response.status_code, status_code)
        _get_page(self.mozillian_client, 200)
        _get_page(self.mozillian2_client, 200)
        _get_page(self.pending_client, 302)
        _get_page(self.incomplete_client, 302)
        _get_page(self.anonymous_client, 302)

    def test_user_view_public_mozillian_profile(self):
        """Test user requests public mozillian profile."""
        def _get_page(client, status_code):
            url = reverse('profile', args=[self.mozillian2.username])
            response = client.get(url)
            eq_(response.status_code, status_code)
        _get_page(self.mozillian_client, 200)
        _get_page(self.mozillian2_client, 200)
        _get_page(self.pending_client, 200)
        _get_page(self.incomplete_client, 200)
        _get_page(self.anonymous_client, 200)

    def test_user_view_pending_profile(self):
        """Test user requests pending profile."""
        def _get_page(client, status_code):
            url = reverse('profile', args=[self.pending.username])
            response = client.get(url)
            eq_(response.status_code, status_code)
        _get_page(self.mozillian_client, 200)
        _get_page(self.mozillian2_client, 200)
        _get_page(self.pending_client, 200)
        _get_page(self.incomplete_client, 200)
        _get_page(self.anonymous_client, 200)

        # Set pending profile to non public
        self.pending.userprofile.privacy_full_name = MOZILLIANS
        self.pending.userprofile.save()
        _get_page(self.mozillian_client, 200)
        _get_page(self.mozillian2_client, 200)
        _get_page(self.pending_client, 200)
        _get_page(self.incomplete_client, 302)
        _get_page(self.anonymous_client, 302)

    def test_user_view_non_existand_profile(self):
        """Test user requests non existand profile."""
        def _get_page(client, status_code):
            url = reverse('profile', args=['foo-bar'])
            response = client.get(url)
            eq_(response.status_code, status_code)
        _get_page(self.mozillian_client, 404)
        _get_page(self.mozillian2_client, 404)
        _get_page(self.pending_client, 302)
        _get_page(self.incomplete_client, 302)
        _get_page(self.anonymous_client, 302)

    def test_user_view_incomplete_profile(self):
        """Test user requests incomplete profile."""
        def _get_page(client, status_code):
            url = reverse('profile', args=[self.incomplete.username])
            response = client.get(url)
            eq_(response.status_code, status_code)
        _get_page(self.mozillian_client, 404)
        _get_page(self.mozillian2_client, 404)
        _get_page(self.pending_client, 302)
        _get_page(self.incomplete_client, 200)
        _get_page(self.anonymous_client, 302)

    def test_pending_edit_profile(self):
        # do all then reset
        newbie_client = self.pending_client
        newbie = self.pending

        profile_url = reverse('profile', args=[newbie.username])
        edit_profile_url = reverse('profile.edit')
        # original
        r = newbie_client.get(profile_url)
        newbie = r.context['profile']
        full = newbie.full_name
        bio = newbie.bio

        # update
        data = self.data_privacy_fields.copy()
        data.update(dict(full_name='Hobo LaRue', country='pl', bio='Rides the rails'))
        edit = newbie_client.post(edit_profile_url, data, follow=True)
        eq_(200, edit.status_code, 'Edits okay')
        r = newbie_client.get(profile_url)
        newbie = r.context['profile']
        self.assertNotEqual(full, newbie.full_name)
        self.assertNotEqual(bio, newbie.bio)

        # cleanup
        delete_url = reverse('profile.delete')

        r = newbie_client.post(delete_url, follow=True)
        eq_(200, r.status_code, 'A Mozillian can delete their own account')

    def test_profile_photo(self):
        """Make sure profile photo uploads and removals work.

        Test the upload, encoding, and removal of photo profiles. Also
        make sure edge cases (from naughty user input) and HTML
        elements work properly.

        .. note::

            This does not test that the web server is serving the files
            from the filesystem properly.
        """
        client = self.mozillian_client
        # No photo exists by default, the delete photo form control shouldn't
        # be present, and trying to delete a non-existant photo shouldn't
        # do anything.
        self.assert_no_photo(client)

        # Try to game the form -- it shouldn't do anything.
        data = self.data_privacy_fields.copy()
        data.update({'full_name': 'foo', 'country': 'pl', 'photo-clear': 1})
        r = client.post(reverse('profile.edit'), data)
        eq_(r.status_code, 302, 'Trying to delete a non-existant photo '
                                "shouldn't result in an error.")

        # Add a profile photo
        filename = os.path.join(os.path.dirname(__file__), 'profile-photo.jpg')
        with open(filename, 'rb') as f:
            data = self.data_privacy_fields.copy()
            data.update(dict(full_name='foo', country='pl', photo=f))
            r = client.post(reverse('profile.edit'), data)

        eq_(r.status_code, 302, 'Form should validate and redirect the user.')

        r = client.get(reverse('profile.edit'))
        doc = pq(r.content)

        assert doc('#id_photo_delete'), (
                '"Remove Profile Photo" control should appear.')
        assert r.context['profile'].photo

        # Remove a profile photo
        data.update({'full_name': 'foo', 'photo-clear': 1, 'photo': None})
        r = client.post(reverse('profile.edit'), data)

        eq_(r.status_code, 302, 'Form should validate and redirect the user.')

        self.assert_no_photo(client)

    def assert_no_photo(self, client):
        """This will assert that a user is in a proper no userpic state.

        This means:
            * Linking to 'unknown.jpg'.
            * No 'Remove Profile Photo' link.
            * No file on the file system.
        """
        r = client.get(reverse('profile.edit'))
        doc = pq(r.content)
        assert not doc('#id_photo_delete'), (
                '"Remove Profile Photo" control should not appear.')

        # make sure no file is in the file system
        f = self.mozillian.get_profile().photo
        assert not f

    def test_default_picture_is_gravatar(self):
        self.client.login(email=self.pending.email)
        self.assert_no_photo(self.client)
        doc = pq(self.client.get(
                 reverse('profile', args=[self.pending.username])).content)

        img = doc('.profile-photo')[0].getchildren()[0]
        assert 'gravatar' in img.attrib['src']

    def test_has_website(self):
        """Verify a user's website appears in their profile (as a link)."""
        self.client.login(email=self.mozillian.email)

        client = self.client

        # No website URL is present.
        r = client.get(reverse('profile.edit'))
        doc = pq(r.content)

        assert not doc('#dd.website'), (
                'No website info appears on the user\'s profile.')

        # Add a URL sans protocol.
        data = self.data_privacy_fields.copy()
        data.update(dict(full_name='foo', country='pl', website='tofumatt.com'))
        r = client.post(reverse('profile.edit'), data)
        eq_(r.status_code, 302, 'Submission works and user is redirected.')
        r = client.get(reverse('profile', args=[self.mozillian.username]))
        doc = pq(r.content)

        assert ('http://tofumatt.com/' in
                doc('#profile-info li.url a')[0].get('href')), (
            'User should have a URL with protocol added.')

    def test_has_country(self):
        u = user(username='sam', full_name='sam')
        p = u.get_profile()
        p.country = 'us'
        p.save()
        assert self.client.login(email=u.email)
        r = self.client.get(reverse('profile', args=[u.username]), follow=True)
        self.assertContains(r, p.country)

    def test_has_region(self):
        u = user(username='sam', full_name='sam')
        p = u.get_profile()
        p.country = 'us'
        p.region = 'New York'
        p.save()
        assert self.client.login(email=u.email)
        r = self.client.get(reverse('profile', args=[u.username]), follow=True)
        self.assertContains(r, p.region)

    def test_has_city(self):
        u = user(username='sam', full_name='sam')
        p = u.get_profile()
        p.country = 'us'
        p.region = 'New York'
        p.city = 'Brooklyn'
        p.save()
        assert self.client.login(email=u.email)
        r = self.client.get(reverse('profile', args=[u.username]), follow=True)
        self.assertContains(r, p.region)
        self.assertContains(r, p.city)

    def test_replace_photo(self):
        """Ensure we can replace photos."""
        client = self.mozillian_client

        filename = os.path.join(os.path.dirname(__file__), 'profile-photo.jpg')
        with open(filename, 'rb') as f:
            data = self.data_privacy_fields.copy()
            data.update(dict(full_name='foo', country='pl', photo=f), follow=True)
            response = client.post(reverse('profile.edit'), data, follow=True)
            doc = pq(response.content)
            old_photo = doc('.profile-photo')[0].getchildren()[0].attrib['src']

        with open(filename, 'rb') as f:
            data = self.data_privacy_fields.copy()
            data.update(dict(full_name='foo', country='pl', photo=f), follow=True)
            response = client.post(reverse('profile.edit'), data, follow=True)
            doc = pq(response.content)
            new_photo = doc('.profile-photo')[0].getchildren()[0].attrib['src']
        assert new_photo != old_photo


class TestVouch(ESTestCase):
    """This is implemented as its own class so that we can avoid
    mucking up the included users.

    """

    def test_mozillian_can_vouch(self):
        """
        Tests the vouching system's happy path.

        Kind of a big test because we want to:
        a. Test registration's happy path
        b. Test vouching
        c. Test account deletion
        """
        moz_client = self.mozillian_client
        r = moz_client.get(reverse('profile', args=[self.pending.username]))
        eq_(200, r.status_code)
        doc = pq(r.content)
        self.assertTrue(doc('form#vouch-form'))

        vouch_url = reverse('vouch')
        data = dict(vouchee=self.pending.get_profile().id)
        vouched_profile = moz_client.post(vouch_url, data, follow=True)
        self.pending = User.objects.get(pk=self.pending.pk)
        eq_(200, vouched_profile.status_code)

        r = moz_client.get(reverse('profile', args=[self.pending.username]))
        eq_(200, r.status_code)
        doc = pq(r.content)
        self.assertTrue(not doc('form#vouch-form'))

        eq_(self.pending.get_profile().vouched_by.user, self.mozillian,
            'Credit given')


class TestOpensearchViews(ESTestCase):
    """Tests for the OpenSearch plugin, accessible to anonymous visitors."""

    def test_search_plugin(self):
        """The plugin loads with the correct mimetype."""
        response = self.client.get(reverse('search_plugin'))
        eq_(200, response.status_code)
        assert 'expires' in response
        eq_('application/opensearchdescription+xml', response['content-type'])

    def test_localized_search_plugin(self):
        """Every locale gets its own plugin."""
        response = self.client.get(reverse('search_plugin'))
        assert '/en-US/search' in response.content

        # Prefixer and its locale are sticky; clear it before the next request
        set_url_prefix(None)
        response = self.client.get(reverse('search_plugin', prefix='/fr/'))
        assert '/fr/search' in response.content


def _logged_in_html(response):
    doc = pq(response.content)
    return doc('a#logout')


def _create_new_user():
    newbie_client = test.Client()
    newbie_email = '%s@test.net' % str(uuid4())[0:8]
    reg_url = reverse('register')
    params = dict(username=str(uuid4())[0:8],
                  email=newbie_email,
                  password='asdfasdf',
                  confirmp='asdfasdf',
                  full_name='Newbie McPal',
                  optin='True')
    r = newbie_client.post(reg_url, params, follow=True)
    eq_('registration/login.html', r.templates[0].name)

    u = User.objects.filter(email=params['email'])[0].get_profile()
    u.save()

    r = newbie_client.login(email=newbie_email)

    r = newbie_client.get(reverse('profile', args=[u.user.username]))
    eq_('phonebook/profile.html', r.templates[0].name)

    return (u.user, newbie_client)
