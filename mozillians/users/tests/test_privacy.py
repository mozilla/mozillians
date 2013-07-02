from nose.tools import eq_

from mozillians.common.tests.init import ESTestCase
from mozillians.users.models import EMPLOYEES, PRIVILEGED, UserProfile


class PrivacyTests(ESTestCase):

    def test_privacy_fields(self):
        """Test privacy fields."""
        self.mozillian.userprofile.set_privacy_level(PRIVILEGED)
        up = (UserProfile.objects
              .privacy_level(EMPLOYEES).get(user=self.mozillian))

        for field, value in UserProfile._privacy_fields.items():
            eq_(getattr(up, field), value)
