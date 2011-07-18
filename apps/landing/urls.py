from django.conf.urls.defaults import patterns, url
from django.contrib import admin

from . import views

admin.autodiscover()

urlpatterns = patterns('',
    url('^$', views.home, name='home'),
    url('^robots.txt$', views.robots, name='robots.txt'),
    url('^about$', views.about, name='landing.about'),
)
