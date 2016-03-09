from django_jinja import library

from mozillians.announcements.models import Announcement


@library.global_function
def latest_announcement():
    """Return the latest published announcement or None."""

    if Announcement.objects.published().count():
        return Announcement.objects.published().latest()
    return None
