from django.conf import settings
from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()

from . import views

urlpatterns = patterns('',
    url('^$', views.home, name='landing.home'),
    url('^robots.txt$', views.robots, name='robots.txt'),
    url('^about$', views.about, name='landing.about'),
)
