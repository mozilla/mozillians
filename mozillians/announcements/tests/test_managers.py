from datetime import datetime

from mock import patch
from nose.tools import eq_

from mozillians.announcements.models import Announcement
from mozillians.announcements.tests import AnnouncementFactory, TestCase


class AnnouncementManagerTests(TestCase):
    def setUp(self):
        AnnouncementFactory.create(
            publish_from=datetime(2013, 2, 12),
            publish_until=datetime(2013, 2, 18))
        AnnouncementFactory.create(
            publish_from=datetime(2013, 2, 15),
            publish_until=datetime(2013, 2, 17))
        AnnouncementFactory.create(
            publish_from=datetime(2013, 2, 21),
            publish_until=datetime(2013, 2, 23))

    @patch('mozillians.announcements.managers.datetime')
    def test_published(self, mock_obj):
        """Test published() of Announcement Manager."""
        mock_obj.now.return_value = datetime(2013, 2, 10)
        eq_(Announcement.objects.published().count(), 0)

        mock_obj.now.return_value = datetime(2013, 2, 13)
        eq_(Announcement.objects.published().count(), 1)

        mock_obj.now.return_value = datetime(2013, 2, 16)
        eq_(Announcement.objects.published().count(), 2)

        mock_obj.now.return_value = datetime(2013, 2, 19)
        eq_(Announcement.objects.published().count(), 0)

        mock_obj.now.return_value = datetime(2013, 2, 24)
        eq_(Announcement.objects.published().count(), 0)

    @patch('mozillians.announcements.managers.datetime')
    def test_unpublished(self, mock_obj):
        """Test unpublished() of Announcement Manager."""
        mock_obj.now.return_value = datetime(2013, 2, 10)
        eq_(Announcement.objects.unpublished().count(), 3)

        mock_obj.now.return_value = datetime(2013, 2, 13)
        eq_(Announcement.objects.unpublished().count(), 2)

        mock_obj.now.return_value = datetime(2013, 2, 16)
        eq_(Announcement.objects.unpublished().count(), 1)

        mock_obj.now.return_value = datetime(2013, 2, 19)
        eq_(Announcement.objects.unpublished().count(), 3)

        mock_obj.now.return_value = datetime(2013, 2, 24)
        eq_(Announcement.objects.unpublished().count(), 3)
