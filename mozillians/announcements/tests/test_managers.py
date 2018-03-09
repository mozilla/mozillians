import pytz
from datetime import datetime

from mock import patch
from nose.tools import eq_

from django.utils.timezone import make_aware

from mozillians.announcements.models import Announcement
from mozillians.announcements.tests import AnnouncementFactory, TestCase


class AnnouncementManagerTests(TestCase):
    def setUp(self):
        AnnouncementFactory.create(
            publish_from=make_aware(datetime(2013, 2, 12), pytz.UTC),
            publish_until=make_aware(datetime(2013, 2, 18), pytz.UTC))
        AnnouncementFactory.create(
            publish_from=make_aware(datetime(2013, 2, 15), pytz.UTC),
            publish_until=make_aware(datetime(2013, 2, 17), pytz.UTC))
        AnnouncementFactory.create(
            publish_from=make_aware(datetime(2013, 2, 21), pytz.UTC),
            publish_until=make_aware(datetime(2013, 2, 23), pytz.UTC))

    @patch('mozillians.announcements.managers.now')
    def test_published(self, mock_obj):
        """Test published() of Announcement Manager."""
        mock_obj.return_value = make_aware(datetime(2013, 2, 10), pytz.UTC)
        eq_(Announcement.objects.published().count(), 0)

        mock_obj.return_value = make_aware(datetime(2013, 2, 13), pytz.UTC)
        eq_(Announcement.objects.published().count(), 1)

        mock_obj.return_value = make_aware(datetime(2013, 2, 16), pytz.UTC)
        eq_(Announcement.objects.published().count(), 2)

        mock_obj.return_value = make_aware(datetime(2013, 2, 19), pytz.UTC)
        eq_(Announcement.objects.published().count(), 0)

        mock_obj.return_value = make_aware(datetime(2013, 2, 24), pytz.UTC)
        eq_(Announcement.objects.published().count(), 0)

    @patch('mozillians.announcements.managers.now')
    def test_unpublished(self, mock_obj):
        """Test unpublished() of Announcement Manager."""
        mock_obj.return_value = make_aware(datetime(2013, 2, 10), pytz.UTC)
        eq_(Announcement.objects.unpublished().count(), 3)

        mock_obj.return_value = make_aware(datetime(2013, 2, 13), pytz.UTC)
        eq_(Announcement.objects.unpublished().count(), 2)

        mock_obj.return_value = make_aware(datetime(2013, 2, 16), pytz.UTC)
        eq_(Announcement.objects.unpublished().count(), 1)

        mock_obj.return_value = make_aware(datetime(2013, 2, 19), pytz.UTC)
        eq_(Announcement.objects.unpublished().count(), 3)

        mock_obj.return_value = make_aware(datetime(2013, 2, 24), pytz.UTC)
        eq_(Announcement.objects.unpublished().count(), 3)
