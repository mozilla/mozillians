from datetime import datetime

from mock import patch
from nose.tools import ok_, eq_
from pytz import utc

from django.test.utils import override_settings
from django.utils.timezone import is_aware

from mozillians.common.tests import TestCase
from mozillians.common.utils import aware_utcnow, now_in_timezone, offset_of_timezone


class TestAwareUTCNow(TestCase):
    @override_settings(USE_TZ=False)
    def test_aware_now_if_use_tz_false(self):
        # aware_utcnow returns an aware time, even if USE_TZ is False
        ok_(is_aware(aware_utcnow()))

    @override_settings(USE_TZ=True)
    def test_aware_now_if_use_tz_true(self):
        # aware_utcnow returns an aware time, even if USE_TZ is True
        ok_(is_aware(aware_utcnow()))


class TestNowInTimezone(TestCase):
    def test_now_in_timezone(self):
        # now_in_timezone returns the current time, expressed in the desired timezone
        # Construct a time in UTC that will be "now"
        utc_time = datetime(1972, 1, 1, 12, 4, 5).replace(tzinfo=utc)
        tz_name = "US/Eastern"  # 5 hours difference from UTC on 1/1/1972
        with patch('mozillians.common.utils.aware_utcnow') as mock_aware_now:
            mock_aware_now.return_value = utc_time
            result = now_in_timezone(tz_name)
        ok_(is_aware(result))
        fmt_time = result.strftime("%H:%M %Z")
        eq_('07:04 EST', fmt_time)


class TestOffsetOfTimezone(TestCase):
    def test_offset_of_timezone(self):
        # offset_of_timezone returns the offset in minutes of the named timezone as of now
        # Construct a time in UTC that will be "now"
        utc_time = datetime(1972, 1, 1, 3, 4, 5).replace(tzinfo=utc)
        tz_name = "US/Eastern"  # 5 hours difference from UTC on 1/1/1972
        with patch('mozillians.common.utils.aware_utcnow') as mock_aware_now:
            mock_aware_now.return_value = utc_time
            result = offset_of_timezone(tz_name)
        eq_(-300, result)
