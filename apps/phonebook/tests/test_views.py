from uuid import uuid4

from django import test

from nose.tools import eq_
from pyquery import PyQuery as pq

from funfactory.urlresolvers import reverse
from phonebook.tests import (LDAPTestCase, AMANDA_NAME, AMANDEEP_NAME,
                             AMANDEEP_VOUCHER, MOZILLIAN, PENDING,
                             OTHER_MOZILLIAN, PASSWORD, mozillian_client)
from phonebook.views import UNAUTHORIZED_DELETE


class TestDeleteUser(LDAPTestCase):
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
        for user in [MOZILLIAN, PENDING]:
            self._delete_flow(user)

    def _delete_flow(self, user):
        """Private method used to walk through account deletion flow."""
        client = mozillian_client(user['email'])
        uniq_id = user['uniq_id']

        r = client.get(reverse('phonebook.edit_profile', args=[uniq_id]))
        doc = pq(r.content)

        # Make sure there's a link to a confirm deletion page, and nothing
        # pointing directly to the delete URL.
        eq_(reverse('confirm_delete'), doc('#delete-profile').attr('href'),
            'We see a link to a confirmation page.')
        self.assertFalse(any((reverse('phonebook.delete_profile') in el.action)
                              for el in doc('#main form')),
            "We don't see a form posting to the account delete URL.")

        # Follow the link to the deletion confirmation page.
        r = client.get(doc('#delete-profile').attr('href'))

        # Test that we can go back (i.e. cancel account deletion).
        doc = pq(r.content)
        eq_(reverse('phonebook.edit_profile', args=[uniq_id]),
            doc('#cancel-action').attr('href'))

        # Test that account deletion works.
        delete_url = doc('#delete-action').closest('form').attr('action')
        r = client.post(delete_url, {'unique_id': uniq_id}, follow=True)
        eq_(200, r.status_code)
        self.assertFalse(_logged_in_html(r))

        # Make sure the user can't login anymore
        client = test.Client()
        data = dict(username=user['email'], password=PASSWORD)
        r = client.post(reverse('login'), data, follow=True)
        self.assertFalse(_logged_in_html(r))


class TestViews(LDAPTestCase):

    def test_anonymous_home(self):
        r = self.client.get('/', follow=True)
        self.assertEquals(200, r.status_code)
        doc = pq(r.content)
        login = reverse('login')
        eq_(doc('a#login').attr('href'), login, 'We see a link to login')
        self.assertFalse(_logged_in_html(r))

    def test_pending_home(self):
        r = self.pending_client.get('/', follow=True)
        self.assertEquals(200, r.status_code)
        self.assertTrue(_logged_in_html(r))
        doc = pq(r.content)
        profile = reverse('profile', args=[PENDING['uniq_id']])
        eq_(profile, doc('a#profile').attr('href'),
            'We see a link to our profile')

    def test_mozillian_home(self):
        r = self.mozillian_client.get('/', follow=True)
        self.assertEquals(200, r.status_code)
        self.assertTrue(_logged_in_html(r))
        doc = pq(r.content)
        profile = reverse('profile', args=[MOZILLIAN['uniq_id']])
        eq_(profile, doc('a#profile').attr('href'),
            'We see a link to our profile')

    def test_anonymous_or_pending_search(self):
        search = reverse('phonebook.search')

        r = self.client.get(search, dict(q='Am'), follow=True)
        self.assertFalse('people' in r.context)

        r = self.pending_client.get(search, dict(q='Am'), follow=True)
        eq_(r.context.get('people', []), [])

    def test_mozillian_search(self):
        url = reverse('phonebook.search')
        r = self.mozillian_client.get(url, dict(q='Am'))
        peeps = r.context['people']
        saw_amandeep = saw_amanda = False

        for person in peeps:
            if person.full_name == AMANDEEP_NAME:
                eq_(AMANDEEP_VOUCHER, person.voucher_unique_id,
                    'Amandeep is a Mozillian')
                saw_amandeep = True
            elif person.full_name == AMANDA_NAME:
                if person.voucher_unique_id:
                    self.fail('Amanda is pending status')
                saw_amanda = True
            if saw_amandeep and saw_amanda:
                break
        self.assertTrue(saw_amandeep, 'We see Mozillians')
        self.assertTrue(saw_amanda, 'We see Pending')

    def test_mozillian_sees_mozillian_profile(self):
        url = reverse('profile', args=[OTHER_MOZILLIAN['uniq_id']])
        r = self.mozillian_client.get(url)
        eq_(AMANDEEP_NAME, r.context['person'].full_name)

    def test_mozillian_can_vouch(self):
        """
        Tests the vouching system's happy path.

        Kind of a big test because we want to:
        a. Test registration's happy path
        b. Test vouching
        c. Test account deletion
        """
        newbie_uniq_id, newbie_client = _create_new_user()
        newbie_profile_url = reverse('profile', args=[newbie_uniq_id])
        name = 'Newbie McPal'

        moz_client = self.mozillian_client

        profile = moz_client.get(newbie_profile_url)
        eq_(name, profile.context['person'].full_name,
            'Regisration worked and we can see their profile')
        # test for vouch form...
        self.assertTrue(profile.context['vouch_form'], 'Newb needs a voucher')
        vouch_url = reverse('phonebook.vouch')
        data = dict(voucher=MOZILLIAN['uniq_id'], vouchee=newbie_uniq_id)
        vouched_profile = moz_client.post(vouch_url, data, follow=True)
        eq_(200, vouched_profile.status_code)
        eq_('phonebook/profile.html', vouched_profile.templates[0].name)

        profile = moz_client.get(newbie_profile_url)
        eq_(name, profile.context['person'].full_name,
            "Vouching worked and we're back on Newbie's profile")
        voucher = profile.context['person'].voucher

        eq_(MOZILLIAN['uniq_id'], voucher.unique_id,
            'Credit given')
        self.assertFalse(vouched_profile.context['vouch_form'],
                         'No need to vouch for this confirmed Mozillian')
        delete_url = reverse('phonebook.delete_profile')

        try:
            data = dict(unique_id=newbie_uniq_id)
            moz_client.post(delete_url, data, follow=True)
            self.assertFail("A Mozillian can't delete another account")
        except UNAUTHORIZED_DELETE:
            pass

        data = dict(unique_id=newbie_uniq_id)
        delete = newbie_client.post(delete_url, data, follow=True)
        eq_(200, delete.status_code,
            'A Mozillian can delete their own account')

        profile = moz_client.get(newbie_profile_url)
        eq_(404, profile.status_code)

    def test_pending_edit_profile(self):
        # do all then reset
        newbie_uniq_id, newbie_client = _create_new_user()
        profile_url = reverse('profile', args=[newbie_uniq_id])
        edit_profile_url = reverse('phonebook.edit_profile',
                                   args=[newbie_uniq_id])
        # original
        r = newbie_client.get(profile_url)
        newbie = r.context['person']
        first = newbie.first_name
        last = newbie.last_name
        bio = newbie.biography

        # update
        data = dict(first_name='Hobo', last_name='LaRue',
                    biography='Rides the rails')
        edit = newbie_client.post(edit_profile_url, data, follow=True)
        eq_(200, edit.status_code, 'Edits okay')
        r = newbie_client.get(profile_url)
        newbie = r.context['person']
        self.assertNotEqual(first, newbie.first_name)
        self.assertNotEqual(last,  newbie.last_name)
        self.assertNotEqual(bio,   newbie.biography)

        display_name = "%s %s" % (newbie.first_name, newbie.last_name)
        eq_(display_name, newbie.full_name,
                         'Editing should update display name')
        # cleanup
        delete_url = reverse('phonebook.delete_profile')
        data = dict(unique_id=newbie_uniq_id)

        r = newbie_client.post(delete_url, data, follow=True)
        eq_(200, r.status_code, 'A Mozillian can delete their own account')

    def test_my_profile(self):
        """Are we cachebusting our picture?"""
        profile = reverse('profile', args=[MOZILLIAN['uniq_id']])
        r = self.mozillian_client.get(profile)
        doc = pq(r.content)
        assert '?' in doc('#profile-photo').attr('src')


def _logged_in_html(response):
    doc = pq(response.content)
    return doc('a#logout') and doc('a#profile')


def _create_new_user():
    newbie_client = test.Client()
    newbie_email = '%s@test.net' % str(uuid4())[0:8]
    reg_url = reverse('register')
    params = dict(email=newbie_email,
                  password='asdfasdf',
                  confirmp='asdfasdf',
                  first_name='Newbie',
                  last_name='McPal',
                  optin='True')
    r = newbie_client.post(reg_url, params, follow=True)
    eq_('phonebook/edit_profile.html', r.templates[0].name)
    newbie_uniq_id = r.context['person'].unique_id
    if not newbie_uniq_id:
        msg = 'New user should be logged in and have a uniqueIdentifier'
        raise Exception(msg)
    return (newbie_uniq_id, newbie_client)
