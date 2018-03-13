from datetime import datetime

from django.utils.timezone import make_aware, utc

from jinja2 import Markup
from mock import patch
from nose.tools import ok_

from mozillians.announcements.tests import AnnouncementFactory, TestCase


class AnnouncementTests(TestCase):
    @patch('mozillians.announcements.models.now')
    def test_published(self, mock_obj):
        """Test published model property."""
        first = AnnouncementFactory.create(
            publish_from=make_aware(datetime(2013, 2, 12), utc),
            publish_until=make_aware(datetime(2013, 2, 18), utc))
        second = AnnouncementFactory.create(
            publish_from=make_aware(datetime(2013, 2, 15), utc),
            publish_until=make_aware(datetime(2013, 2, 17), utc))
        third = AnnouncementFactory.create(
            publish_from=make_aware(datetime(2013, 2, 21), utc),
            publish_until=make_aware(datetime(2013, 2, 23), utc))

        mock_obj.return_value = make_aware(datetime(2013, 2, 16), utc)
        ok_(first.published)
        ok_(second.published)
        ok_(not third.published)

    def test_get_template_text(self):
        announcement = AnnouncementFactory.create(publish_from=datetime(2013, 2, 12))
        text = announcement.get_template_text()
        ok_(isinstance(text, Markup))
