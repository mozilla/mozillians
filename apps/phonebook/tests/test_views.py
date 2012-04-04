import os
from uuid import uuid4

from django import test
from django.contrib.auth.models import User

import test_utils
from nose.tools import eq_
from pyquery import PyQuery as pq

from common.tests import TestCase, ESTestCase
from funfactory.urlresolvers import set_url_prefix, reverse


class TestDeleteUser(TestCase):
    """Separate test class used to test account deletion flow.

    We create a separate class to delete a user because other tests depend
    on Mozillian users existing.
    """

    def test_confirm_delete(self):
        """Test the account deletion flow, including confirmation.

        A user should not be presented with a form/link that allows them to
        delete their account without a confirmation page. Once they access that
        page, they should be presented with a link to "go back" to their
        profile or to permanently delete their account.

        This test is abstracted away to a generic user deletion flow so
        we can test both non-vouched and vouched user's ability to delete
        their own profile.
        """

        for user in [self.mozillian, self.pending]:
            self._delete_flow(user)

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
            doc('#delete_profile').attr('href'),
            'We see a link to a confirmation page.')
        self.assertFalse(any((reverse('profile.delete') in el.action)
                              for el in doc('#main form')),
            "We don't see a form posting to the account delete URL.")

        # Follow the link to the deletion confirmation page.
        r = self.client.get(doc('#delete_profile').attr('href'))

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
        assert not User.objects.get(id=user_id).email
        assert not User.objects.get(id=user_id).is_active


class TestViews(TestCase):
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

    def test_anonymous_or_pending_search(self):
        return
        search = reverse('search')

        r = self.client.get(search, dict(q='Am'), follow=True)
        self.assertFalse('people' in r.context)

        self.client.login(email=self.pending.email)
        r = self.client.get(search, dict(q='Am'), follow=True)
        eq_(r.context.get('people', []), [])

    def test_mozillian_sees_mozillian_profile(self):
        user = User.objects.create(
                username='other', email='whatever@whatver.man')

        url = reverse('profile', args=['other'])
        r = self.mozillian_client.get(url)
        eq_(r.status_code, 200)
        eq_(r.context['profile'].user, user)

    def test_pending_edit_profile(self):
        # do all then reset
        newbie_client = self.pending_client
        newbie = self.pending

        profile_url = reverse('profile', args=[newbie.username])
        edit_profile_url = reverse('profile.edit')
        # original
        r = newbie_client.get(profile_url)
        newbie = r.context['profile']
        first = newbie.user.first_name
        last = newbie.user.last_name
        bio = newbie.bio

        # update
        data = dict(first_name='Hobo', last_name='LaRue',
                    bio='Rides the rails')
        edit = newbie_client.post(edit_profile_url, data, follow=True)
        eq_(200, edit.status_code, 'Edits okay')
        r = newbie_client.get(profile_url)
        newbie = r.context['profile']
        self.assertNotEqual(first, newbie.user.first_name)
        self.assertNotEqual(last,  newbie.user.last_name)
        self.assertNotEqual(bio,   newbie.bio)

        dn = "%s %s" % (newbie.user.first_name, newbie.user.last_name)
        eq_(dn, newbie.display_name, 'Editing should update display name')

        # cleanup
        delete_url = reverse('profile.delete')

        r = newbie_client.post(delete_url, follow=True)
        eq_(200, r.status_code, 'A Mozillian can delete their own account')

    def test_profile_photo(self):
        """Make sure profile photo uploads and removals work.

        Test the upload, encoding, and removal of photo profiles. Also make
        sure edge cases (from naughty user input) and HTML elements work
        properly.

        .. note::

           This does not test that the web server is serving the files from
           the filesystem properly.
        """
        client = self.mozillian_client

        def assert_no_photo():
            """This will assert that a user is in a proper no userpic state.

            This means:
                * Linking to ``unknown.jpg``.
                * No "Remove Profile Photo" link.
                * No file on the file system.
            """
            r = client.get(reverse('profile.edit'))
            doc = pq(r.content)
            assert not doc('#id_photo_delete'), (
                    '"Remove Profile Photo" control should not appear.')

            # make sure no file is in the file system
            f = self.mozillian.get_profile().photo
            assert not f

        # No photo exists by default, the delete photo form control shouldn't
        # be present, and trying to delete a non-existant photo shouldn't
        # do anything.
        assert_no_photo()

        # Try to game the form -- it shouldn't do anything.
        r = client.post(reverse('profile.edit'),
                {'last_name': 'foo', 'photo-clear': 1})
        eq_(r.status_code, 302, 'Trying to delete a non-existant photo'
                                "shouldn't result in an error.")

        # Add a profile photo
        f = open(os.path.join(os.path.dirname(__file__), 'profile-photo.jpg'),
                 'rb')
        r = client.post(reverse('profile.edit'),
                        dict(last_name='foo', photo=f))
        f.close()
        eq_(r.status_code, 302, 'Form should validate and redirect the user.')

        r = client.get(reverse('profile.edit'))
        doc = pq(r.content)

        assert doc('#id_photo_delete'), (
                '"Remove Profile Photo" control should appear.')

        assert self.mozillian.userprofile.photo

        # Remove a profile photo
        r = client.post(reverse('profile.edit'),
                {'last_name': 'foo', 'photo-clear': 1})

        eq_(r.status_code, 302, 'Form should validate and redirect the user.')

        assert_no_photo()

    def test_has_website(self):
        """Verify a user's website appears in their profile (as a link)."""
        self.client.login(email=self.mozillian.email)

        client = self.client

        # No website URL is present.
        r = client.get(reverse('profile.edit'))
        doc = pq(r.content)

        assert not doc('#dd.website'), (
                "No website info appears on the user's profile.")

        # Add a URL sans protocol.
        r = client.post(reverse('profile.edit'),
                        dict(last_name='foo', website='tofumatt.com'))
        eq_(r.status_code, 302, 'Submission works and user is redirected.')
        r = client.get(reverse('profile', args=[self.mozillian.username]))
        doc = pq(r.content)

        assert('http://tofumatt.com/' in [a.get('href') for a in doc('#profile-info dd a')], (
                'User should have a URL with protocol added.'))

    def test_replace_photo(self):
        """Ensure we can replace photos."""
        client = self.mozillian_client
        f = open(os.path.join(os.path.dirname(__file__), 'profile-photo.jpg'),
                 'rb')
        r = client.post(reverse('profile.edit'),
                dict(last_name='foo', photo=f), follow=True)

        f.close()

        f = open(os.path.join(os.path.dirname(__file__), 'profile-photo.jpg'),
                 'rb')
        doc = pq(r.content)
        old_photo = doc('#profile-photo').attr('src')
        r = client.post(reverse('profile.edit'),
                        dict(last_name='foo', photo=f), follow=True)
        f.close()
        doc = pq(r.content)
        new_photo = doc('#profile-photo').attr('src')
        assert new_photo != old_photo


class TestVouch(TestCase):
    """
    This is implemented as its own class
    so that we can avoid mucking up the included
    users
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


class TestOpensearchViews(test_utils.TestCase):
    """Tests for the OpenSearch plugin, accessible to anonymous visitors"""
    def test_search_plugin(self):
        """The plugin loads with the correct mimetype."""
        response = self.client.get(reverse('search_plugin'))
        eq_(200, response.status_code)
        assert 'expires' in response
        eq_('application/opensearchdescription+xml', response['content-type'])

    def test_localized_search_plugin(self):
        """Every locale gets its own plugin!"""
        response = self.client.get(reverse('search_plugin'))
        assert '/en-US/search' in response.content

        # Prefixer and its locale are sticky; clear it before the next request
        set_url_prefix(None)
        response = self.client.get(reverse('search_plugin',
                                   prefix='/fr/'))
        assert '/fr/search' in response.content


class TestSearch(ESTestCase):
    def test_mozillian_search(self):
        """Test our search."""
        amanda = 'Amanda Younger'
        amandeep = 'Amandeep McIlrath'
        url = reverse('search')
        r = self.mozillian_client.get(url, dict(q='Am'))
        rs = self.mozillian_client.get(url, dict(q=' Am'))
        rnv = self.mozillian_client.get(url, dict(q='Am', nonvouched_only=1))

        eq_(r.status_code, 200)
        peeps = r.context['people']
        peeps_ws = rs.context['people']
        peeps_nv = rnv.context['people']

        saw_amandeep = saw_amanda = False

        for person in peeps:
            if person.display_name == amandeep:
                assert person.is_vouched, 'Amandeep is a Mozillian'
                saw_amandeep = True
            elif person.display_name == amanda:
                if person.is_vouched:
                    self.fail('Amanda is pending status')
                saw_amanda = True
            if saw_amandeep and saw_amanda:
                break

        assert peeps[0].id in (peeps_ws[0].id, peeps_ws[1].id)
        self.assertEqual(peeps_nv[0].display_name, amanda)
        self.assertTrue(saw_amandeep, 'We see Mozillians')
        self.assertTrue(saw_amanda, 'We see Pending')

        assert all(not person.is_vouched for person in peeps_nv)

    def test_mozillian_search_pagination(self):
        """Tests the pagination on search.

        1. assumes no page is passed, but valid limit is passed
        2. assumes invalid page is passed, no limit is passed
        3. assumes valid page is passed, no limit is passed
        4. assumes valid page is passed, valid limit is passed
        """
        url = reverse('search')
        r = self.mozillian_client.get(url, dict(q='Amand', limit='1'))
        peeps = r.context['people']
        self.assertEqual(len(peeps), 1)

        r = self.mozillian_client.get(url, dict(q='Amand', page='test'))
        peeps = r.context['people']
        self.assertEqual(len(peeps), 2)

        r = self.mozillian_client.get(url, dict(q='Amand', page='1'))
        peeps = r.context['people']
        self.assertEqual(len(peeps), 2)

        r = self.mozillian_client.get(url, dict(q='Amand', page='test',
                                                limit='1'))
        peeps = r.context['people']
        self.assertEqual(len(peeps), 1)

        r = self.mozillian_client.get(url, dict(q='Amand', page='test',
                                                limit='x'))
        peeps = r.context['people']
        self.assertEqual(len(peeps), 2)

        r = self.mozillian_client.get(url, dict(q='Amand', page='test',
                                                limit='-3'))
        peeps = r.context['people']
        self.assertEqual(len(peeps), 2)


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
                  first_name='Newbie',
                  last_name='McPal',
                  optin='True')
    r = newbie_client.post(reg_url, params, follow=True)
    eq_('registration/login.html', r.templates[0].name)

    u = User.objects.filter(email=params['email'])[0].get_profile()
    u.save()

    r = newbie_client.login(email=newbie_email)

    r = newbie_client.get(reverse('profile', args=[u.user.username]))
    eq_('phonebook/profile.html', r.templates[0].name)

    return (u.user, newbie_client)
