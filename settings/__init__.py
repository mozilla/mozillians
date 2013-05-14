from funfactory.settings_base import *
from settings.initial import *
from settings.default import *

try:
    from settings.local import *
except ImportError:
    pass

if DATABASES['default']['NAME'] and DATABASES['default']['USER'] and DATABASES['default']['PASSWORD'] is None:
  raise NotConfigured
  
