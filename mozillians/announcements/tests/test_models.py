from datetime import datetime

from jinja2 import Markup
from mock import patch
from nose.tools import ok_

from mozillians.announcements.tests import AnnouncementFactory, TestCase


class AnnouncementTests(TestCase):
    @patch('mozillians.announcements.models.datetime')
    def test_published(self, mock_obj):
        """Test published model property."""
        first = AnnouncementFactory.create(publish_from=datetime(2013, 2, 12),
                                           publish_until=datetime(2013, 2, 18))
        second = AnnouncementFactory.create(publish_from=datetime(2013, 2, 15),
                                            publish_until=datetime(2013, 2, 17))
        third = AnnouncementFactory.create(publish_from=datetime(2013, 2, 21),
                                           publish_until=datetime(2013, 2, 23))

        mock_obj.now.return_value = datetime(2013, 2, 16)
        ok_(first.published)
        ok_(second.published)
        ok_(not third.published)

    def test_get_template_text(self):
        announcement = AnnouncementFactory.create(publish_from=datetime(2013, 2, 12))
        text = announcement.get_template_text()
        ok_(isinstance(text, Markup))
