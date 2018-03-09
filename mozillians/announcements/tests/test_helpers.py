import pytz
from datetime import datetime

from django.utils.timezone import make_aware
from mock import patch
from nose.tools import eq_

from mozillians.announcements.templatetags.helpers import latest_announcement
from mozillians.announcements.tests import AnnouncementFactory, TestCase


class AnnouncementManagerTests(TestCase):

    @patch('mozillians.announcements.managers.now')
    def test_announcement_helper(self, mock_obj):
        """Test latest announcement helper."""
        first = AnnouncementFactory.create(
            publish_from=make_aware(datetime(2013, 2, 12), pytz.UTC),
            publish_until=make_aware(datetime(2013, 2, 18), pytz.UTC))
        second = AnnouncementFactory.create(
            publish_from=make_aware(datetime(2013, 2, 15), pytz.UTC),
            publish_until=make_aware(datetime(2013, 2, 17), pytz.UTC))
        third = AnnouncementFactory.create(
            publish_from=make_aware(datetime(2013, 2, 21), pytz.UTC),
            publish_until=make_aware(datetime(2013, 2, 23), pytz.UTC))

        mock_obj.return_value = make_aware(datetime(2013, 2, 13), pytz.UTC)
        eq_(latest_announcement(), first)

        mock_obj.return_value = make_aware(datetime(2013, 2, 15), pytz.UTC)
        eq_(latest_announcement(), second)

        mock_obj.return_value = make_aware(datetime(2013, 2, 17), pytz.UTC)
        eq_(latest_announcement(), first)

        mock_obj.return_value = make_aware(datetime(2013, 2, 19), pytz.UTC)
        eq_(latest_announcement(), None)

        mock_obj.return_value = make_aware(datetime(2013, 2, 22), pytz.UTC)
        eq_(latest_announcement(), third)
