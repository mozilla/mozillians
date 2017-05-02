import factory

from mozillians.api.models import APIv2App


class APIv2AppFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'App {0}'.format(n))
    description = factory.Sequence(lambda n: 'Description for App {0}'.format(n))
    enabled = True

    class Meta:
        model = APIv2App
