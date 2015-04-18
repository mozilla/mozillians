from django.forms import model_to_dict

from mock import MagicMock, patch
from mozillians.geo.tests import CountryFactory
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.groups.models import Skill
from mozillians.phonebook.forms import EmailForm, ExternalAccountForm, ProfileForm
from mozillians.users.tests import UserFactory


class EmailFormTests(TestCase):
    def test_email_changed_false(self):
        user = UserFactory.create(email='foo@bar.com')
        form = EmailForm({'email': 'foo@bar.com'},
                         initial={'email': user.email, 'user_id': user.id})
        form.full_clean()
        ok_(not form.email_changed())

    def test_email_changed_true(self):
        user = UserFactory.create(email='foo@bar.com')
        form = EmailForm({'email': 'bar@bar.com'},
                         initial={'email': user.email, 'user_id': user.id})
        form.full_clean()
        ok_(form.email_changed())


class ProfileFormTests(TestCase):
    def test_skill_name_validation(self):
        # skill names can contain A-Za-z0-9 +.:-
        user = UserFactory.create(email='foo@bar.com')
        data = model_to_dict(user.userprofile)

        # valid names
        data['skills'] = 'lO ngN,am3+.:-'
        form = ProfileForm(data=data, instance=user.userprofile)
        ok_(form.is_valid(), msg=dict(form.errors))

        # Save the form
        form.save()
        # We should end up with two skills - note the names are lower-cased
        ok_(Skill.objects.filter(name='lo ngn').exists())
        ok_(Skill.objects.filter(name='am3+.:-').exists())

        # an invalid name - ';' is not a valid character
        data['skills'] = 'lOngName+.:-;'
        form = ProfileForm(data=data, instance=user.userprofile)
        ok_(not form.is_valid())
        ok_('skills' in form.errors)

    def test_story_link(self):
        user = UserFactory.create()
        data = model_to_dict(user.userprofile)
        data['story_link'] = 'http://somelink.com'
        form = ProfileForm(data=data, instance=user.userprofile)
        ok_(form.is_valid(), msg=dict(form.errors))

        eq_(form.cleaned_data['story_link'], u'http://somelink.com/')

        data['story_link'] = 'Foobar'
        form = ProfileForm(data=data, instance=user.userprofile)
        ok_(not form.is_valid())

    def test_lat_lng_does_not_point_to_country(self):
        # If form includes lat/lng, must point to some country; fails if not
        user = UserFactory.create(email='foo@bar.com')
        data = model_to_dict(user.userprofile)
        # invalid data
        data['lat'] = data['lng'] = 0.0
        form = ProfileForm(data=data, instance=user.userprofile)
        with patch('mozillians.users.models.UserProfile.reverse_geocode'):
            # Pretend that geocoding doesn't come up with a country
            user.userprofile.geo_country = None
            ok_(not form.is_valid())

    def test_lat_lng_does_point_to_country(self):
        # If form includes lat/lng, must point to some country; succeeds if so
        user = UserFactory.create(email='foo@bar.com')
        data = model_to_dict(user.userprofile)
        # Try again, with valid data
        data['lng'] = 35.918596
        data['lat'] = -79.083799
        country = CountryFactory.create()
        form = ProfileForm(data=data, instance=user.userprofile)
        with patch('mozillians.users.models.UserProfile.reverse_geocode'):
            # Pretend that geocoding does come up with a country
            user.userprofile.geo_country = country
            ok_(form.is_valid())


class ExternalAccountFormTests(TestCase):
    def test_identifier_cleanup(self):
        with patch('mozillians.phonebook.forms.ExternalAccount.ACCOUNT_TYPES',
                   {'AMO': {'name': 'Example',
                            'url': 'https://example.com/{identifier}'}}):
            form = ExternalAccountForm({'type': 'AMO',
                                        'identifier': 'https://example.com/foobar/',
                                        'privacy': 3})
            form.is_valid()
        eq_(form.cleaned_data['identifier'], 'foobar')

    def test_identifier_validator_get_called(self):
        validator = MagicMock()
        with patch('mozillians.phonebook.forms.ExternalAccount.ACCOUNT_TYPES',
                   {'AMO': {'name': 'Example',
                            'validator': validator}}):
            form = ExternalAccountForm({'type': 'AMO',
                                        'identifier': 'https://example.com/foobar/',
                                        'privacy': 3})
            form.is_valid()
        ok_(validator.called)

    def test_account_with_url_but_no_identifier(self):
        # Related bug 984298
        with patch('mozillians.phonebook.forms.ExternalAccount.ACCOUNT_TYPES',
                   {'AMO': {'name': 'Example',
                            'url': 'https://example.com/{identifier}'}}):
            form = ExternalAccountForm({'type': 'AMO',
                                        'privacy': 3})
            form.is_valid()
        ok_('identifier' in form.errors)
