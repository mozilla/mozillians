# Code based on funfactory with some modification in order to work with django 1.7
# https://github.com/mozilla/funfactory/blob/master/funfactory/monkeypatches.py
import logging
from django.conf import settings

__all__ = ['patch']


# Idempotence! http://en.wikipedia.org/wiki/Idempotence
_has_patched = False


def patch():
    global _has_patched
    if _has_patched:
        return

    # Monkey-patch Django's csrf_protect decorator to use session-based CSRF
    # tokens:
    if 'session_csrf' in settings.INSTALLED_APPS:
        import session_csrf
        session_csrf.monkeypatch()

    logging.debug("Note: funfactory monkey patches executed in %s" % __file__)

    # prevent it from being run again later
    _has_patched = True
