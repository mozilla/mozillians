from django.conf import settings
from django.conf.urls.defaults import include, patterns

from django.contrib import admin

import jingo


admin.autodiscover()


def _error_page(request, status):
    """
    Render error pages with jinja2. Error templates are in the root
    /templates directory.
    """
    return jingo.render(request, '%d.html' % status, status=status)


handler404 = lambda r: _error_page(r, 404)
handler500 = lambda r: _error_page(r, 500)
handler_csrf = lambda r, cb=None: jingo.render(r, 'csrf_error.html', status=400)


urlpatterns = patterns('',
    (r'', include('landing.urls')),
    (r'', include('phonebook.urls')),
    (r'', include('users.urls')),

    (r'^admin/', include(admin.site.urls)),
)

# In DEBUG mode, serve media files through Django, and serve error pages
# via predictable routes.
if settings.DEBUG:
    # Remove leading and trailing slashes so the regex matches.
    media_url = settings.MEDIA_URL.lstrip('/').rstrip('/')
    urlpatterns += patterns('',
        (r'^%s/(?P<path>.*)$' % media_url, 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT}),
        # Add the 404, 500, and csrf pages for testing
        (r'^404$', handler404),
        (r'^500$', handler500),
        (r'^csrf$', handler_csrf),
    )
