#import test_utils
from uuid import uuid4

from django.utils import unittest
from django import test

from commons.urlresolvers import reverse

from phonebook.views import UNAUTHORIZED_DELETE


#class TestViews(test_utils.TestCase):
class TestViews(unittest.TestCase):
    def setUp(self):
        self.anon_client = test.Client()
        self.pending_client = self._pending_user()
        self.mozillian_client = self._mozillian_user()

    def _pending_user(self):
        client = test.Client()
        # We can't use client.login for these tests
        url = reverse('login')
        client.post(url, {'username': 'u000003@mozillians.org',
                     'password': 'secret'}, follow=True)
        # HACK Something is seriously hozed here...
        # First visit to /login always fails, so we make
        # second request... WTF
        client = test.Client()
        url = reverse('login')
        home = client.post(url, {'username': 'u000003@mozillians.org',
                            'password': 'secret'}, follow=True)
        self.assertEqual('u000003@mozillians.org', str(home.context['user']))
        return client

    def _mozillian_user(self):
        client = test.Client()
        # We can't use c.login for these tests
        url = reverse('login')
        home = client.post(url, {'username': 'u000001@mozillians.org',
                            'password': 'secret'}, follow=True)
        self.assertEqual('u000001@mozillians.org', str(home.context['user']))
        return client

    def tearDown(self):
        pass

    def test_anonymous_home(self):
        home = self.anon_client.get('/', follow=True)
        self.assertEquals(200, home.status_code)
        self.assertTrue('/login">' in home.content,
                   "Anonymous traffic sees a login link")
        self.assertFalse(_logged_in_html(home))

    def test_pending_home(self):
        home = self.pending_client.get('/', follow=True)
        self.assertEquals(200, home.status_code)
        self.assertTrue(_logged_in_html(home))
        self.assertTrue('/u/7f3a67u000003' in home.content,
                        "We see a link to our profile")

    def test_mozillian_home(self):
        home = self.mozillian_client.get('/', follow=True)
        self.assertEquals(200, home.status_code)
        self.assertTrue(_logged_in_html(home))
        self.assertTrue('/u/7f3a67u000001' in home.content,
                        "We see a link to our profile")

    def test_anonymous_or_pending_search(self):
        for client in [self.anon_client, self.pending_client]:
            search = client.get('/search', {'q': 'Am'}, follow=True)
            peeps = search.context['people']
            self.assertEqual(0, len(peeps),
                            "Search should fail for Interlopers")

    def test_mozillian_search(self):
        url = reverse('phonebook.search')
        search = self.mozillian_client.get(url, {'q': 'Am'})
        if not search:
            self.fail("No search page")
        if not search.context:
            self.fail("No search page context")
        peeps = search.context['people']
        saw_amandeep = saw_amanda = False
        for person in peeps:
            if person['cn'][0] == 'Amandeep McIlrath':
                saw_amandeep = True
            elif person['cn'][0] == 'Amanda Younger':
                saw_amanda = True
            if saw_amandeep and saw_amanda:
                break

        self.assertTrue(saw_amandeep, "We see Mozillians")
        self.assertTrue(saw_amanda, "We see Pending")

    def test_mozillian_sees_mozillian_profile(self):
        url = reverse('profile', args=['7f3a67u000098'])
        profile = self.mozillian_client.get(url)
        self.assertEqual(['Amandeep McIlrath'],
                         profile.context['person']['cn'])

    def test_mozillian_can_vouch(self):
        """
        Kind of a big test because we want to
        a) test registration's happy path
        b) test vouching
        c) test account deletion
        """
        newbie_uniq_id, newbie_client = _create_new_user()
        newbie_profile_url = reverse('profile', args=[newbie_uniq_id])

        profile = self.mozillian_client.get(newbie_profile_url)
        self.assertEqual(['Newbie McPal'], profile.context['person']['cn'],
                         "Regisration worked and we can see their profile")
        # test for vouch form...
        self.assertTrue(profile.context['vouch_form'], "Newb needs a voucher")
        vouch_url = reverse('phonebook.vouch')
        vouched_profile = self.mozillian_client.post(vouch_url,
                            dict(voucher='7f3a67u000001',
                                 vouchee=newbie_uniq_id),
                            follow=True)
        self.assertEqual(200, vouched_profile.status_code)
        self.assertEqual(['Newbie McPal'], profile.context['person']['cn'],
                         "Vouching worked and we're back on Newbie's profile")
        self.assertFalse(vouched_profile.context['vouch_form'],
                         "No need to vouch for this confirmed Mozillian")
        delete_url = reverse('phonebook.delete_profile')

        try:
            self.mozillian_client.post(delete_url,
                                       dict(uniqueIdentifier=newbie_uniq_id),
                                       follow=True)
            self.assertFail("A Mozillian can't delete another account")
        except UNAUTHORIZED_DELETE:
            pass

        delete = newbie_client.post(delete_url,
                                    dict(uniqueIdentifier=newbie_uniq_id),
                                    follow=True)
        self.assertEqual(200, delete.status_code,
                         "A Mozillian can delete their own account")

        profile = self.mozillian_client.get(newbie_profile_url)
        self.assertEqual(404, profile.status_code)

    def test_pending_edit_profile(self):
        # do all then reset
        newbie_uniq_id, newbie_client = _create_new_user()
        profile_url = reverse('profile', args=[newbie_uniq_id])
        edit_profile_url = reverse('phonebook.edit_profile',
                                   args=[newbie_uniq_id])
        # original
        profile = newbie_client.get(profile_url)
        newbie = profile.context['person']
        first  = newbie['givenName'][0]
        last   = newbie['sn'][0]
        if 'description' in newbie:
            bio = newbie['description'][0]
        else:
            bio = None

        # update
        edit = newbie_client.post(edit_profile_url,
                                       dict(first_name='Hobo',
                                            last_name='LaRue',
                                            biography='Rides the rails'),
                                  follow=True)
        self.assertEqual(200, edit.status_code, "Edits okay")
        profile = newbie_client.get(profile_url)
        newbie = profile.context['person']
        self.assertNotEqual(first, newbie['givenName'][0])
        self.assertNotEqual(last,  newbie['sn'][0])
        self.assertNotEqual(bio,   newbie['description'][0])

        display_name = "%s %s" % (newbie['givenName'][0], newbie['sn'][0])
        self.assertEqual(display_name, newbie['displayName'][0],
                         "Editing should update display name")
        # cleanup
        delete_url = reverse('phonebook.delete_profile')
        delete = newbie_client.post(delete_url,
                                    dict(uniqueIdentifier=newbie_uniq_id),
                                    follow=True)
        self.assertEqual(200, delete.status_code,
                         "A Mozillian can delete their own account")


def _logged_in_html(response):
    return 'Profile' in response.content and\
           '/logout">Log' in response.content


def _create_new_user():
    newbie_client = test.Client()
    newbie_email = "%s@test.net" % str(uuid4())[0:8]
    reg_url = reverse('register')
    params = {'email': newbie_email,
              'password': 'asdfasdf',
              'confirmp': 'asdfasdf',
              'first_name': 'Newbie',
              'last_name': 'McPal',
              'optin': 'True'}
    home = newbie_client.post(reg_url,
                              params,
                              follow=True)
    ldap_user = home.context['user'].ldap_user
    newbie_uniq_id = ldap_user.attrs['uniqueIdentifier'][0]
    if not newbie_uniq_id:
        raise Exception("New user should be logged in and have " +
                  "a uniqueIdentifier")
    return (newbie_uniq_id, newbie_client)
