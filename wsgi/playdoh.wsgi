import os
import site

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mozillians.settings')
os.environ.setdefault('CELERY_LOADER', 'django')

# Add `mozillians` to the python path
wsgidir = os.path.dirname(__file__)
site.addsitedir(os.path.abspath(os.path.join(wsgidir, '../')))

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
