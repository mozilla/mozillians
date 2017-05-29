from django.forms import model_to_dict

from mock import MagicMock, patch
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.phonebook.forms import (ContributionForm, EmailForm, ExternalAccountForm,
                                        filter_vouched)
from mozillians.users.models import UserProfile
from mozillians.users.tests import UserFactory


class TestFilterVouched(TestCase):
    def test_only_vouched(self):
        UserFactory.create_batch(4, vouched=True)
        UserFactory.create_batch(3, vouched=False)
        qs = UserProfile.objects.all()
        eq_(filter_vouched(qs, 'yes').count(), 4)

    def test_only_unvouched(self):
        UserFactory.create_batch(4, vouched=False)
        UserFactory.create_batch(3, vouched=True)
        qs = UserProfile.objects.all()
        eq_(filter_vouched(qs, 'no').count(), 4)


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


class ProfileFormsTests(TestCase):

    def test_story_link(self):
        user = UserFactory.create()
        data = model_to_dict(user.userprofile)
        data['story_link'] = 'http://somelink.com'
        form = ContributionForm(data=data, instance=user.userprofile)
        ok_(form.is_valid(), msg=dict(form.errors))

        eq_(form.cleaned_data['story_link'], u'http://somelink.com')

        data['story_link'] = 'Foobar'
        form = ContributionForm(data=data, instance=user.userprofile)
        ok_(not form.is_valid())


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
