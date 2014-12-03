from django.conf import settings
from django.conf.urls import include, patterns, url
from django.contrib import admin
from django.shortcuts import render

import autocomplete_light
import tower
from funfactory.monkeypatches import patch


# Funfactory monkeypatches
patch()

autocomplete_light.autodiscover()
admin.autodiscover()

# From socorro
# funfactory puts the more limited CompressorExtension extension in
# but we need the one from jingo_offline_compressor.jinja2ext otherwise we
# might an error like this:
#
# AttributeError: 'CompressorExtension' object has no attribute 'nodelist'
#
from jingo_offline_compressor.jinja2ext import CompressorExtension
import jingo
try:
    jingo.env.extensions.pop(
        'compressor.contrib.jinja2ext.CompressorExtension'
    )
except KeyError:
    # happens if the urlconf is loaded twice
    pass
jingo.env.add_extension(CompressorExtension)

# Activate a locale so that jinja2 doesn't choke when running a shell
# or individual tests that need translation and don't involve a web
# request, like when testing emails.
tower.activate('en-US')


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


urlpatterns = patterns(
    '',
    url(r'', include('django_browserid.urls')),
    url(r'^api/', include('mozillians.api.urls')),
    url(r'', include('mozillians.groups.urls', 'groups')),
    url(r'', include('mozillians.phonebook.urls', 'phonebook')),

    # Admin URLs.
    url(r'^admin/', include(admin.site.urls)),
    url(r'^_autocomplete/', include('autocomplete_light.urls')),

    url(r'', include('mozillians.humans.urls', 'humans')),
)

# In DEBUG mode, serve media files through Django, and serve error pages
# via predictable routes. Add in qunit tests.
if settings.DEBUG:
    # Remove leading and trailing slashes so the regex matches.
    urlpatterns += patterns(
        '',
        # Add the 404, 500, and csrf pages for testing
        url(r'^404/$', handler404),
        url(r'^500/$', handler500),
        url(r'^csrf/$', handler_csrf),
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT}))
