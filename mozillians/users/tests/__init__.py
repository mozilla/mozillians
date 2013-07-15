from django.contrib.auth.models import User

import factory


class UserFactory(factory.DjangoModelFactory):
    FACTORY_FOR = User
    username = factory.Sequence(lambda n: 'user{0}'.format(n))
    first_name = 'Joe'
    last_name = factory.Sequence(lambda n: 'Doe {0}'.format(n))
    email = factory.LazyAttribute(
        lambda a: '{0}.{1}@example.com'.format(
            a.first_name, a.last_name.replace(' ', '.')))

    @factory.post_generation
    def userprofile(self, create, extracted, **kwargs):
        self.userprofile.full_name = ' '.join([self.first_name, self.last_name])
        self.userprofile.country = 'gr'
        if extracted:
            for key, value in extracted.items():
                setattr(self.userprofile, key, value)
        self.userprofile.save()
