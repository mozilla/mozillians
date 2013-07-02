from django.contrib.auth.models import User

from mozillians.common.tests.init import ESTestCase
from mozillians.users.tasks import remove_incomplete_accounts


class IncompleteAccountsTest(ESTestCase):
    """Incomplete accounts removal tests."""

    def test_remove_incomplete_accounts(self):
        """Test remove incomplete accounts."""
        query = User.objects.filter(userprofile__full_name='')
        self.assertGreater(query.count(), 0)
        remove_incomplete_accounts(days=0)
        query = User.objects.filter(userprofile__full_name='')
        self.assertEqual(query.count(), 0)
