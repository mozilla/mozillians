import sys

from .base import *


try:
    from .local import *
except ImportError, exc:
    exc.args = tuple(['%s (did you rename settings/local.py-dist?)'
                      % exc.args[0]])
    raise exc


TEST = len(sys.argv) > 1 and sys.argv[1] == 'test'
if TEST:
    try:
        from .test import *
    except ImportError:
        pass
