from datetime import datetime

from pytz import timezone, utc


def aware_utcnow():
    """
    Return timezone-aware now, same way Django does it, but regardless
    of settings.USE_TZ. (This is a separate method so it can be easily
    mocked to test the other methods.)
    """
    return datetime.utcnow().replace(tzinfo=utc)


def now_in_timezone(timezone_name):
    """
    Return the current time, expressed in the named timezone
    """
    zone = timezone(timezone_name)
    return zone.normalize(aware_utcnow().astimezone(zone))


def offset_of_timezone(timezone_name):
    """
    Return offset from UTC of named time zone, in minutes, as of now.

    This is (time in specified time zone) - (time UTC), so if the time
    zone is 5 hours ahead of UTC, it returns 300.
    """
    now = now_in_timezone(timezone_name)
    offset = now.tzinfo.utcoffset(now)  # timedelta
    minutes = offset.seconds / 60 + offset.days * 24 * 60
    return minutes
