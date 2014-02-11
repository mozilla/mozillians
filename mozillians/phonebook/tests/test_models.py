from mock import Mock

from django.template.loader import get_template
from django.core import mail

from mozillians.common.tests import TestCase
from mozillians.phonebook import InviteFactory
from mozillians.users.tests import UserFactory



"""for the tests, I'd mock send_mail and check the everything
is as expected, morinonaka"""

class InviteTests(TestCase):

    def setUp(self):
        user = UserFactory.create()
        self.invitation = InviteFactory(inviter=user.userprofile)
        mail.send_mail = Mock()

#    def test_invite_template_exists(self):
#        template = get_template('phonebook/invite_email.txt')


    def test_sends_mail_correctly(self):
        self.invitation.send()
