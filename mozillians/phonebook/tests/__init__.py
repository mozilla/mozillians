import factory

from mozillians.phonebook.models import Invite


class InviteFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Invite
    recipient = factory.Sequence(lambda n: 'user{0}@example.com'.format(n))
    message = 'This is invite message'
