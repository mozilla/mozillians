from django.conf import settings
from django.conf.urls.defaults import patterns, url

from django.contrib import admin
admin.autodiscover()

from . import views

urlpatterns = patterns('',
    url('^u/(?P<userid>.*)$', views.profile_uid, name='phonebook.profile_uid'),
    url('^user/photo/(?P<stable_id>.*)$', views.photo,
        name='phonebook.profile_uid'),

    # url('^n/(?P<nickname>.*)$', views.profile, name='phonebook.profile'),
    # Post 1.0?
    url('^user/edit/(?P<userid>.*)$', views.edit_profile,
        name='phonebook.edit_profile'),
    url('^search$', views.search, name='phonebook.search'),
    #url('^tag/(?P<tag>.*)$', views.tag, name='phonebook.tag'),
    # Post 1.0?
    url('^invite$', views.invite, name='phonebook.invite'),

    # Move to auth?
    #url('^login$', views.login, name='phonebook.login'),
    #url('^registration(/(?P<invitetoken>.*))?$', views.registration,
    #    name='phonebook.registration'),

)

## In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    # Remove leading and trailing slashes so the regex matches.
    media_url = settings.MEDIA_URL.lstrip('/').rstrip('/')
    urlpatterns += patterns('',
        (r'^%s/(?P<path>.*)$' % media_url, 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT}),
    )
