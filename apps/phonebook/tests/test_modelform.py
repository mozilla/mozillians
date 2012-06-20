from funfactory.urlresolvers import reverse
from nose.tools import eq_
from pyquery import PyQuery as pq

from common.tests import TestCase, user


class ModelForms(TestCase):
    def test_edit_unavailable_form_field(self):
        newbie_client = self.pending_client
        newbie = self.pending
        # make sure we're at a good starting state
        assert not newbie.get_profile().is_vouched

        edit_profile_url = reverse('profile.edit')

        bad_data = dict(first_name='BadHobo', last_name='BadLaRue',
                        bio='Rides the rails', is_vouched=True)

        bad_edit = newbie_client.post(edit_profile_url, bad_data, follow=True)
        eq_(bad_edit.status_code, 200)

        newbie_profile = bad_edit.context['profile']
        assert not newbie_profile.is_vouched
        eq_(newbie_profile.user.first_name, bad_data['first_name'])

    def test_username_filled_in(self):
        """The username field should have a type and value."""
        newbie = user(username='sam', email='sam@sam.com')

        url = reverse('profile.edit')
        assert self.client.login(email=newbie.email)
        response = self.client.get(url, follow=True)

        eq_(200, response.status_code)
        doc = pq(response.content)
        field = doc('#id_username')[0]
        eq_('input', field.tag)
        assert 'value' in field.attrib
        eq_('text', field.attrib['type'])
        eq_(newbie.username, field.attrib['value'])
