from django.conf import settings
from django.conf.urls.defaults import include, patterns, url
from django.contrib import admin
from django.shortcuts import render
from django.views.decorators.cache import cache_page
from django.views.generic.base import TemplateView
from django.views.i18n import javascript_catalog

import autocomplete_light

from apps.common.decorators import allow_public

autocomplete_light.autodiscover()
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
    url(r'^browserid/', include('django_browserid.urls')),
    url(r'^api/', include('api.urls')),
    url(r'', include('users.urls')),
    url(r'', include('groups.urls')),
    url(r'', include('phonebook.urls')),

    # Admin URLs.
    url(r'^admin/', include(admin.site.urls)),
    url(r'^_autocomplete/', include('autocomplete_light.urls')),

    url(r'^jsi18n/$',
        allow_public(cache_page(60 * 60 * 24 * 365)(javascript_catalog)),
        {'domain': 'javascript', 'packages': ['mozillians']}, name='jsi18n'),
)

# In DEBUG mode, serve media files through Django, and serve error pages
# via predictable routes. Add in qunit tests.
if settings.DEBUG:
    # Remove leading and trailing slashes so the regex matches.
    media_url = settings.MEDIA_URL.lstrip('/').rstrip('/')
    urlpatterns += patterns('',
        (r'^%s/(?P<path>.*)' % media_url, 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT}),
        # Add the 404, 500, and csrf pages for testing
        (r'^404/$', handler404),
        (r'^500/$', handler500),
        (r'^csrf/$', handler_csrf),

        url(r'^test/qunit/$', TemplateView.as_view(template_name='qunit.html'),
            name="qunit_test"),
    )
