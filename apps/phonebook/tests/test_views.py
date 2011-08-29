from uuid import uuid4

from django import test

from nose.tools import eq_
from pyquery import PyQuery as pq
import test_utils

from funfactory.urlresolvers import reverse
from phonebook.views import UNAUTHORIZED_DELETE

# The test data (below in module constants) must matches data in
# directory/mozillians-bulk-test-data.ldif
# You must have run x-rebuild before these tests
MOZILLIAN = dict(email='u000001@mozillians.org', uniq_id='7f3a67u000001')
PENDING = dict(email='u000003@mozillians.org', uniq_id='7f3a67u000003')
OTHER_MOZILLIAN = dict(email='u000098@mozillians.org', uniq_id='7f3a67u000098')
AMANDEEP_NAME = 'Amandeep McIlrath'
AMANDEEP_VOUCHER = '7f3a67u000001'
AMANDA_NAME = 'Amanda Younger'
PASSWORD = 'secret'


class TestViews(test_utils.TestCase):
    def setUp(self):
        """
        We'll use multiple clients at the same time.
        """
        self.anon_client = self.client
        self.pending_client = self._pending_user()
        self.mozillian_client = self._mozillian_user()

    def _pending_user(self):
        client = test.Client()
        # We can't use client.login for these tests
        url = reverse('login')
        data = dict(username=PENDING['email'], password=PASSWORD)
        client.post(url, data, follow=True)

        # HACK Something is seriously hozed here...
        # First visit to /login always fails, so we make
        # second request... WTF
        client = test.Client()
        url = reverse('login')
        r = client.post(url, data, follow=True)
        eq_(PENDING['email'], str(r.context['user']))
        return client

    def _mozillian_user(self):
        client = test.Client()
        # We can't use c.login for these tests
        url = reverse('login')
        data = dict(username=MOZILLIAN['email'], password=PASSWORD)
        r = client.post(url, data, follow=True)
        eq_(MOZILLIAN['email'], str(r.context['user']))
        return client

    def test_anonymous_home(self):
        r = self.anon_client.get('/', follow=True)
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
        for client in [self.anon_client, self.pending_client]:
            r = client.get(search, dict(q='Am'), follow=True)
            peeps = r.context['people']
            eq_(0, len(peeps),
                'Search should fail for interlopers')

    def test_mozillian_search(self):
        url = reverse('phonebook.search')
        r = self.mozillian_client.get(url, dict(q='Am'))
        peeps = r.context['people']
        saw_amandeep = saw_amanda = False

        for person in peeps:
            if person.full_name == AMANDEEP_NAME:
                eq_(AMANDEEP_VOUCHER,
                    person.voucher_unique_id,
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
