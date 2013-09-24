from nose.tools import ok_

from mozillians.common.tests import TestCase
from mozillians.phonebook.forms import EmailForm
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
