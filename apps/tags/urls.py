from django.conf.urls.defaults import patterns, url

from django.contrib import admin
admin.autodiscover()

from tags import views

urlpatterns = patterns('',
    url('^tags/search$', views.search, name='tag_search'),
)
