from mock import Mock

from django.template.loader import get_template
from django.core import mail

from mozillians.common.tests import TestCase
from mozillians.phonebook.tests import InviteFactory
from mozillians.users.tests import UserFactory
from mozillians.phonebook.models import Invite



"""for the tests, I'd mock send_mail and check the everything
is as expected, morinonaka"""

class InviteTests(TestCase):

    def setUp(self):
        pass

#    def test_invite_template_exists(self):
#        template = get_template('phonebook/invite_email.txt')


    def test_sends_mail_correctly(self):
        user = UserFactory.create()
        #invitation = InviteFactory(inviter=user.userprofile)


        invitation = Invite(
            inviter=user.userprofile,
            recipient='joe@joe.com',
            message='blank')

        invitation.send(sender=user.userprofile)

    def test_sends_mail_without_userprofile(self):
        pass