from datetime import datetime

from mock import patch
from nose.tools import eq_, ok_

from apps.common.tests.init import ESTestCase
from ..helpers import latest_announcement
from ..models import Announcement


class AnnouncementsTests(ESTestCase):
    def setUp(self):
        self.first = Announcement.objects.create(
            title='First', text='First',
            publish_from=datetime(2013, 2, 12),
            publish_until=datetime(2013, 2, 18))
        self.second = Announcement.objects.create(
            title='Second', text='Second',
            publish_from=datetime(2013, 2, 15),
            publish_until=datetime(2013, 2, 17))
        self.third = Announcement.objects.create(
            title='Third', text='Third',
            publish_from=datetime(2013, 2, 21),
            publish_until=datetime(2013, 2, 23))

    @patch('announcements.models.datetime')
    def test_manager_published(self, mock_obj):
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

    @patch('announcements.models.datetime')
    def test_manager_unpublished(self, mock_obj):
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

    @patch('announcements.models.datetime')
    def test_published(self, mock_obj):
        """Test published model property."""

        mock_obj.now.return_value = datetime(2013, 2, 16)
        ok_(self.first.published)
        ok_(self.second.published)
        ok_(not self.third.published)

    @patch('announcements.models.datetime')
    def test_announcement_helper(self, mock_obj):
        """Test latest announcement helper."""

        mock_obj.now.return_value = datetime(2013, 2, 13)
        eq_(latest_announcement(), self.first)

        mock_obj.now.return_value = datetime(2013, 2, 15)
        eq_(latest_announcement(), self.second)

        mock_obj.now.return_value = datetime(2013, 2, 17)
        eq_(latest_announcement(), self.first)

        mock_obj.now.return_value = datetime(2013, 2, 19)
        eq_(latest_announcement(), None)

        mock_obj.now.return_value = datetime(2013, 2, 22)
        eq_(latest_announcement(), self.third)
