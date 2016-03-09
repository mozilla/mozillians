from django.template import engines
from django.test.utils import override_settings
from django.utils.timezone import is_aware

from bleach import clean
from datetime import datetime
from markdown import markdown
from mock import patch
from nose.tools import eq_, ok_
from pytz import utc

from mozillians.common.templatetags import helpers
from mozillians.common.tests import TestCase


class HelperTests(TestCase):
    def setUp(self):
        self.env = engines['jinja2']

    @override_settings(SITE_URL='http://foobar')
    @patch('mozillians.common.templatetags.helpers.settings.DEFAULT_AVATAR_URL', '/foo.jpg')
    def test_gravatar(self):
        avatar_url = helpers.gravatar('fo', size=80, rating='bar')
        eq_(avatar_url, ('https://secure.gravatar.com/avatar/eed8070249'
                         '39b808083f0031a56e9872?s=80&r=bar&d=http%3A%2F%'
                         '2Ffoobar%2Fmedia%2Fimg%2Fdefault_avatar.png'))

    @patch('mozillians.common.templatetags.helpers.markdown_module.markdown', wraps=markdown)
    @patch('mozillians.common.templatetags.helpers.bleach.clean', wraps=clean)
    def test_markdown(self, clean_mock, markdown_mock):
        returned_text = helpers.markdown('***foo***', allowed_tags=['strong'])
        eq_(returned_text, '<strong>foo</strong>')
        ok_(clean_mock.called)
        ok_(markdown_mock.called)

    @override_settings(DEBUG=True)
    def test_display_context(self):
        # With DEBUG on,  display_context() inserts the values of context vars
        t = self.env.from_string('START{{ display_context() }}END')
        c = {'testkey': 'testvalue'}
        s = t.render(c)
        ok_('START<dl' in s)
        ok_('</dl>END' in s)
        ok_("<dt>testkey</dt><dd>'testvalue'</dd>" in s)

    @override_settings(DEBUG=False)
    def test_display_context_production(self):
        # With DEBUG off, display_context() is empty
        t = self.env.from_string('START{{ display_context() }}END')
        c = {'testkey': 'testvalue'}
        s = t.render(c)
        eq_('STARTEND', s)


class TimezoneHelpers(TestCase):
    @override_settings(USE_TZ=False)
    def test_aware_now_if_use_tz_false(self):
        # aware_utcnow returns an aware time, even if USE_TZ is False
        ok_(is_aware(helpers.aware_utcnow()))

    @override_settings(USE_TZ=True)
    def test_aware_now_if_use_tz_true(self):
        # aware_utcnow returns an aware time, even if USE_TZ is True
        ok_(is_aware(helpers.aware_utcnow()))

    def test_now_in_timezone(self):
        # now_in_timezone returns the current time, expressed in the desired timezone
        # Construct a time in UTC that will be "now"
        utc_time = datetime(1972, 1, 1, 12, 4, 5).replace(tzinfo=utc)
        tz_name = "US/Eastern"  # 5 hours difference from UTC on 1/1/1972
        with patch('mozillians.common.templatetags.helpers.aware_utcnow') as mock_aware_now:
            mock_aware_now.return_value = utc_time
            result = helpers.now_in_timezone(tz_name)
        ok_(is_aware(result))
        fmt_time = result.strftime("%H:%M %Z")
        eq_('07:04 EST', fmt_time)

    def test_offset_of_timezone(self):
        # offset_of_timezone returns the offset in minutes of the named timezone as of now
        # Construct a time in UTC that will be "now"
        utc_time = datetime(1972, 1, 1, 3, 4, 5).replace(tzinfo=utc)
        tz_name = "US/Eastern"  # 5 hours difference from UTC on 1/1/1972
        with patch('mozillians.common.templatetags.helpers.aware_utcnow') as mock_aware_now:
            mock_aware_now.return_value = utc_time
            result = helpers.offset_of_timezone(tz_name)
        eq_(-300, result)
