from datetime import datetime

from mock import patch
from nose.tools import eq_

from mozillians.announcements.templatetags.helpers import latest_announcement
from mozillians.announcements.tests import AnnouncementFactory, TestCase


class AnnouncementManagerTests(TestCase):

    @patch('mozillians.announcements.managers.datetime')
    def test_announcement_helper(self, mock_obj):
        """Test latest announcement helper."""
        first = AnnouncementFactory.create(publish_from=datetime(2013, 2, 12),
                                           publish_until=datetime(2013, 2, 18))
        second = AnnouncementFactory.create(publish_from=datetime(2013, 2, 15),
                                            publish_until=datetime(2013, 2, 17))
        third = AnnouncementFactory.create(publish_from=datetime(2013, 2, 21),
                                           publish_until=datetime(2013, 2, 23))

        mock_obj.now.return_value = datetime(2013, 2, 13)
        eq_(latest_announcement(), first)

        mock_obj.now.return_value = datetime(2013, 2, 15)
        eq_(latest_announcement(), second)

        mock_obj.now.return_value = datetime(2013, 2, 17)
        eq_(latest_announcement(), first)

        mock_obj.now.return_value = datetime(2013, 2, 19)
        eq_(latest_announcement(), None)

        mock_obj.now.return_value = datetime(2013, 2, 22)
        eq_(latest_announcement(), third)
