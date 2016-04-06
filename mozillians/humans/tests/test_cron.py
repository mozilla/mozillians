from django.conf import settings

from mock import ANY, mock_open, patch

from mozillians.common.tests import TestCase
from mozillians.humans.cron import generate_humanstxt


class TestCron(TestCase):
    @patch('mozillians.humans.cron._get_githubbers')
    @patch('mozillians.humans.cron.render_to_string')
    def test_generate(self, render_to_string_mock, githubbers_mock):
        render_to_string_mock.return_value = 'rendered'
        githubbers_mock.return_value = ['foo']
        open_mock = mock_open()
        with patch('mozillians.humans.cron.open', open_mock, create=True):
            generate_humanstxt()
        data = {
            'githubbers': ['foo'],
            'localizers': ['foo'],
            'last_update': ANY
        }
        render_to_string_mock.assert_called_with('humans/humans.txt', data)
        open_mock.assert_called_with(settings.HUMANSTXT_FILE, 'w')
        open_mock().write.assert_called_with('rendered')
