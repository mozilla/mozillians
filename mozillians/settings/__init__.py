import sys

from .base import *  # noqa


try:
    from .local import *  # noqa
except ImportError, exc:
    # exc.args = tuple(['%s (did you rename settings/local.py-dist?)'
    #                   % exc.args[0]])
    # raise exc
    pass

TEST = len(sys.argv) > 1 and sys.argv[1] == 'test'
if TEST:
    try:
        from .test import *  # noqa
    except ImportError:
        pass
