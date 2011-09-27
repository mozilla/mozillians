from django.conf import settings
from django.conf.urls.defaults import include, patterns
from django.contrib import admin
from django.shortcuts import render


admin.autodiscover()


def error_page(request, template, status=None):
    """Render error templates, found in the root /templates directory.

    If no status parameter is explcitedly passed, this function assumes
    your HTTP status code is the same as your template name (i.e. passing
    a template=404 will render 404.html with the HTTP status code 404).
    """
    return render(request, '%d.html' % template, status=(status or template))


handler404 = lambda r: error_page(r, 404)
handler500 = lambda r: error_page(r, 500)
handler_csrf = lambda r, cb=None: error_page(r, 'csrf_error', status=400)

urlpatterns = patterns('',
    (r'', include('landing.urls')),
    (r'', include('phonebook.urls')),
    (r'', include('users.urls')),

    #(r'^admin/', include(admin.site.urls)),
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
