from django.contrib.auth.models import Group, User
from django.utils import timezone

import factory
from factory import fuzzy

from mozillians.users.models import Language


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
        self.userprofile.lat = 39.727924
        self.userprofile.lng = 21.592328
        if extracted:
            for key, value in extracted.items():
                setattr(self.userprofile, key, value)
        self.userprofile.save()

    @factory.post_generation
    def manager(self, create, extracted, **kwargs):
        if extracted:
            group, created = Group.objects.get_or_create(name='Managers')
            self.groups.add(group)

    @factory.post_generation
    def vouched(self, create, extracted, **kwargs):
        # By default Users are vouched
        if extracted is None or extracted:
            self.userprofile.is_vouched = True
            self.userprofile.vouches_received.create(
                voucher=None, date=timezone.now(), description='a test autovouch')
        self.userprofile.save()


class LanguageFactory(factory.DjangoModelFactory):
    FACTORY_FOR = Language
    code = fuzzy.FuzzyChoice(choices=['en', 'fr', 'el', 'es'])
