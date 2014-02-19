import factory

from mozillians.phonebook.models import Invite
from mozillians.users.managers import PRIVILEGED
from mozillians.users.models import UserProfilePrivacyModel


class InviteFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Invite
    recipient = factory.Sequence(lambda n: 'user{0}@example.com'.format(n))
    message = 'This is invite message'


def _get_privacy_fields(privacy_level):
    """Helper which returns a dict with privacy fields set to privacy_level"""
    data = {}
    for field in UserProfilePrivacyModel._meta._fields():
        data[field.name] = privacy_level

    # privacy_tshirt field has only one level of privacy available
    data['privacy_tshirt'] = PRIVILEGED
    return data
