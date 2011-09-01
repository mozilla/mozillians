"""
:py:mod:`settings.pre` contains settings that IT will usually override.

The overrides can happen in :py:mod:`settings.pre_local`.

Settings in :py:mod:`settings.default` and :py:mod:`settings.local` depend on
these.
"""

from funfactory.manage import path

#: This is the location of a share used on multiple nodes.  This is a perfect
#: place to store uploaded assets that are shared across webheads.
NETAPP_STORAGE = path('tmp')

#: Base URL for uploaded files. Could be a CDN.
UPLOAD_URL = '/uploads'

try:
    from settings.pre_local import *
except ImportError:
    pass

