import factory
from test_utils import TestCase as BaseTestCase

from mozillians.announcements import models


class TestCase(BaseTestCase):
    pass


class AnnouncementFactory(factory.DjangoModelFactory):
    title = factory.Sequence(lambda n: 'Test Announcement {0}'.format(n))
    text = factory.Sequence(lambda n: 'Text for Announcement {0}'.format(n))

    class Meta:
        model = models.Announcement
