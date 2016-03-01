import factory

from mozillians.funfacts.models import FunFact


class FunFactFactory(factory.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'FunFact {0}'.format(n))
    public_text = factory.Sequence(lambda n: 'Public Test for {0}'.format(n))
    number = 'UserProfile.objects.aggregate(number=Count("id"))'

    class Meta:
        model = FunFact
