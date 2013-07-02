from django.conf.urls.defaults import patterns, url

from mozillians.users import views


urlpatterns = patterns('',
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^register/$', views.register, name='register'))
