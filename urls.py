from django.conf import settings
from django.conf.urls.defaults import *

from django.contrib import admin
from django.contrib import auth
admin.autodiscover()

handler404 = 'landing.views.handler404'
handler500 = 'landing.views.handler500'

urlpatterns = patterns('',
    (r'', include('landing.urls')),
    (r'', include('phonebook.urls')),
    (r'', include('users.urls')),


    (r'^admin/', include(admin.site.urls)),
)

## In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    # Remove leading and trailing slashes so the regex matches.
    media_url = settings.MEDIA_URL.lstrip('/').rstrip('/')
    urlpatterns += patterns('',
        (r'^%s/(?P<path>.*)$' % media_url, 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT}),
    )
