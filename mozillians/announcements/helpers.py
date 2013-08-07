from jingo import register

from models import Announcement


@register.function
def latest_announcement():
    """Return the latest published announcement or None."""
    if Announcement.objects.published().count():
        return Announcement.objects.published().latest()
    return None
