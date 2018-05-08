from nose.tools import eq_

from mozillians.common.tests import TestCase
from mozillians.users.models import IdpProfile, UserProfile
from mozillians.users.tests import UserFactory

from mozillians.phonebook.utils import get_profile_link_by_email


class UtilsTests(TestCase):
    def test_link_email_by_not_found(self):
        user = UserFactory.create()
        link = get_profile_link_by_email(user.email)
        eq_(link, "#")

    def test_link_by_email(self):
        user = UserFactory.create()
        IdpProfile.objects.create(
            profile=user.userprofile,
            auth0_user_id='email|',
            email=user.email,
            primary=False,
            primary_contact_identity=True
        )

        profile = UserProfile.objects.get(pk=user.userprofile.pk)
        link = get_profile_link_by_email(user.email)
        eq_(link, profile.get_absolute_url())
