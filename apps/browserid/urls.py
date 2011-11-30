from django.conf.urls.defaults import patterns, url

from browserid import views

urlpatterns = patterns('',
    url('^browserid-login', views.browserid_login, name='browserid_login'),
)
