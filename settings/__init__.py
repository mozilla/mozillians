from funfactory.settings_base import *
from settings.initial import *
from settings.default import *

try:
    from settings.local import *
except ImportError:
    pass
