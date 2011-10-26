from django.conf.urls.defaults import patterns, url

from django.contrib import admin
admin.autodiscover()

from . import views

urlpatterns = patterns('',
    url('^groups$', views.index, name='group_index'),
    url('^group/(?P<name>.+)$', views.show, name='group'),
    url('^groups/search$', views.search, name='group_search'),
)
