from sys import stdout

from django.core.management import CommandError

from basket import BasketException
from basket.errors import BASKET_UNKNOWN_EMAIL, BASKET_NETWORK_FAILURE
from mock import patch
from nose.tools import ok_

from mozillians.common.tests import TestCase
from mozillians.phonebook.management.commands.check_basket import Command


# valid-looking settings to use
@patch('mozillians.users.tasks.BASKET_API_KEY', new='foo')
@patch('mozillians.users.tasks.BASKET_URL', new='https://basket.example.com')
class CheckBasketTests(TestCase):
    def run_check(self, user_exists=True, http_error=False):
        """
        Run the check and return True if it passed, False otherwise.
        Mocks the actual Basket call.
        `user_exists` is whether Basket should respond as if the user existed.
        `http_error` is whether the basket call should respond as if it couldn't get to Basket
        or Exact Target.
        """
        lookup_path = 'mozillians.phonebook.management.commands.check_basket.lookup_user'
        with patch(lookup_path, autospec=True) as mock_lookup:
            if http_error:
                mock_lookup.side_effect = BasketException(code=BASKET_NETWORK_FAILURE)
            elif not user_exists:
                mock_lookup.side_effect = BasketException(code=BASKET_UNKNOWN_EMAIL)
            else:
                mock_lookup.return_value = {'status': 'ok'}
            cmd = Command()
            cmd.stdout = stdout
            try:
                cmd.handle()
            except CommandError:
                return False
            else:
                return True

    def test_default_case(self):
        # The default test setup will pass the check
        ok_(self.run_check())

    def test_no_user(self):
        # If Basket says there's no such user, the check still passes (at least we got to Basket)
        ok_(self.run_check(user_exists=False))

    def test_bad_url_or_network_problem(self):
        # If the URL request gets back an HTTP error, the check fails
        ok_(not self.run_check(http_error=True))

    # Mozillians has some settings that must be set, or it'll just skip talking to Basket.

    # Note that the tasks module looks these up at import time, and can also
    # get BASKET_API_KEY from the environment, so the checking code looks for
    # them in the tasks module.  Therefore we need to mock the variables in the tasks
    # module rather than overriding settings.

    def test_no_url(self):
        # If BASKET_URL is not set, the check fails
        with patch('mozillians.users.tasks.BASKET_URL', new=None):
            ok_(not self.run_check())

    def test_no_vouched_newsletter(self):
        # If BASKET_VOUCHED_NEWSLETTER is not set, the check fails
        with patch('mozillians.users.tasks.BASKET_VOUCHED_NEWSLETTER', new=None):
            ok_(not self.run_check())

    def test_no_nda_newsletter(self):
        # If BASKET_NDA_NEWSLETTER is not set, the check fails
        with patch('mozillians.users.tasks.BASKET_NDA_NEWSLETTER', new=None):
            ok_(not self.run_check())

    def test_no_api_key(self):
        # If BASKET_API_KEY is not set, the check fails
        with patch('mozillians.users.tasks.BASKET_API_KEY', new=None):
            ok_(not self.run_check())

    def test_multiple_missing_settings(self):
        # If multiple things are missing, check still fails
        with patch('mozillians.users.tasks.BASKET_API_KEY', new=None):
            with patch('mozillians.users.tasks.BASKET_URL', new=None):
                ok_(not self.run_check())
