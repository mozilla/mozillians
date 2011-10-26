from django.conf import settings
from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template

from django.contrib import admin
admin.autodiscover()

from tags import views

urlpatterns = patterns('',
    url('^tags/search$', views.search, name='tag_search'),
)
