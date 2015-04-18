from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import Client
from django.test.utils import override_settings

from funfactory.helpers import urlparams
from mock import patch
from nose.tools import eq_, ok_

from mozillians.common.tests import TestCase
from mozillians.phonebook.tests import InviteFactory
from mozillians.phonebook.utils import redeem_invite
from mozillians.users.tests import UserFactory


class RegisterTests(TestCase):
    def test_register_anonymous(self):
        client = Client()
        url = urlparams(reverse('phonebook:register'), code='foo')
        response = client.get(url, follow=True)
        eq_(client.session['invite-code'], 'foo')
        self.assertTemplateUsed(response, 'phonebook/home.html')

    @override_settings(CAN_VOUCH_THRESHOLD=1)
    @patch('mozillians.phonebook.views.redeem_invite', wraps=redeem_invite)
    def test_register_unvouched(self, redeem_invite_mock):
        user = UserFactory.create(vouched=False)
        inviter = UserFactory.create()
        invite = InviteFactory.create(inviter=inviter.userprofile)
        url = urlparams(reverse('phonebook:register'), code=invite.code)
        with self.login(user) as client:
            response = client.get(url, follow=True)
        user = User.objects.get(id=user.id)
        ok_(user.userprofile.is_vouched)
        ok_(redeem_invite_mock.called)
        self.assertTemplateUsed(response, 'phonebook/home.html')

    @override_settings(CAN_VOUCH_THRESHOLD=1)
    @patch('mozillians.phonebook.views.redeem_invite', wraps=redeem_invite)
    def test_register_vouched(self, redeem_invite_mock):
        voucher_1 = UserFactory.create()
        voucher_2 = UserFactory.create()
        user = UserFactory.create(vouched=False)
        user.userprofile.vouch(voucher_1.userprofile)
        invite = InviteFactory.create(inviter=voucher_2.userprofile)
        url = urlparams(reverse('phonebook:register'), code=invite.code)
        with self.login(user) as client:
            response = client.get(url, follow=True)
        user = User.objects.get(id=user.id)
        ok_(user.userprofile.is_vouched)
        ok_(user.userprofile.vouched_by, voucher_1.userprofile)
        ok_(not redeem_invite_mock.called)
        self.assertTemplateUsed(response, 'phonebook/home.html')

    def test_register_without_code_anonymous(self):
        client = Client()
        response = client.get(reverse('phonebook:register'), follow=True)
        ok_(not self.client.session.get('invite-code'))
        self.assertTemplateUsed(response, 'phonebook/home.html')
        eq_(response.status_code, 200)

    def test_register_without_code_unvouched(self):
        user = UserFactory.create(vouched=False)
        with self.login(user) as client:
            response = client.get(reverse('phonebook:register'), follow=True)
        ok_(not self.client.session.get('invite-code'))
        self.assertTemplateUsed(response, 'phonebook/home.html')
        eq_(response.status_code, 200)

    def test_register_without_code_vouched(self):
        user = UserFactory.create()
        with self.login(user) as client:
            response = client.get(reverse('phonebook:register'), follow=True)
        ok_(not self.client.session.get('invite-code'))
        self.assertTemplateUsed(response, 'phonebook/home.html')
        eq_(response.status_code, 200)
