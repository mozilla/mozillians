from django.conf import settings
from django.conf.urls.defaults import patterns, url

from django.contrib import admin
admin.autodiscover()

from phonebook import views

urlpatterns = patterns('',
    url('^u/(?P<unique_id>.*)$', views.profile_uid, name='profile'),
    url('^user/photo/me$', views.my_photo, name='my_profile_photo'),
    url('^user/photo/(?P<unique_id>.*)$', views.photo,
        name='phonebook.profile_photo'),

    # url('^n/(?P<nickname>.*)$', views.profile, name='phonebook.profile'),
    # Post 1.0?
    url('^user/edit/(?P<unique_id>.*)$', views.edit_profile,
        name='phonebook.edit_profile'),
    url('^register/edit/(?P<unique_id>.*)$', views.edit_new_profile,
        name='phonebook.edit_new_profile'),
    url('^confirm-delete$', views.confirm_delete, name='confirm_delete'),
    url('^delete$', views.delete, name='phonebook.delete_profile'),
    url('^search$', views.search, name='phonebook.search'),
    url('^vouch$', views.vouch, name='phonebook.vouch'),

    url('^invite$', views.invite, name='invite'),
    url('^invited/(?P<id>\d+)$', views.invited, name='invited'),

)

## In DEBUG mode, serve media files through Django.
if settings.DEBUG:
    # Remove leading and trailing slashes so the regex matches.
    media_url = settings.MEDIA_URL.lstrip('/').rstrip('/')
    urlpatterns += patterns('',
        (r'^%s/(?P<path>.*)$' % media_url, 'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT}),
    )
