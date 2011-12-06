from django.conf.urls.defaults import patterns, url

from django.contrib import admin
admin.autodiscover()

from . import views

urlpatterns = patterns('',
    url('^groups$', views.index, name='group_index'),
    url('^groups/(?P<url>[^/]+)$', views.show, name='group'),
    url('^groups/(?P<url>[^/]+)/toggle$', views.toggle, name='group_toggle'),
    url('^groups-search$', views.search, name='group_search'),
)
