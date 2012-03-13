"""
:py:mod:`settings.initial` contains settings that IT will usually override.

The overrides can happen in :py:mod:`settings.initial_local`
(``settings/initial_local.py``).

Settings in :py:mod:`settings.default` and :py:mod:`settings.local` depend on
these.
"""

from funfactory.manage import path

#: This is the location of a share used on multiple nodes.  This is a perfect
#: place to store uploaded assets that are shared across webheads.
NETAPP_STORAGE = path('tmp')

#: Base URL for uploaded files. Could be a CDN.
UPLOAD_URL = '/media/uploads'
#: Should be MEDIA_ROOT in 1.4 but we are set in our ways.
UPLOAD_ROOT = path('media/uploads')

#: This is the base URL for the current instance of the site.
SITE_URL = 'http://mozillians.org'

try:
    from settings.initial_local import *
except ImportError:
    pass
