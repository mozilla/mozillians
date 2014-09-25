import factory

from mozillians.api.models import APIApp, APIv2App
from mozillians.users.tests import UserFactory


class APIAppFactory(factory.DjangoModelFactory):
    FACTORY_FOR = APIApp
    name = factory.Sequence(lambda n: 'App {0}'.format(n))
    description = factory.Sequence(lambda n: 'Description for App {0}'.format(n))
    owner = factory.SubFactory(UserFactory)
    is_active = True


class APIv2AppFactory(factory.DjangoModelFactory):
    FACTORY_FOR = APIv2App
    name = factory.Sequence(lambda n: 'App {0}'.format(n))
    description = factory.Sequence(lambda n: 'Description for App {0}'.format(n))
    enabled = True
