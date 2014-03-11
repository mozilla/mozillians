from django.forms import model_to_dict

from mock import MagicMock, patch
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
