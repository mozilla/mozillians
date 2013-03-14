from django.conf.urls.defaults import patterns, url
from django.contrib.auth import views as auth_views

from jinjautils import jinja_for_django

from users import views

# So we can use the contrib logic for password resets, etc.
auth_views.render_to_response = jinja_for_django


urlpatterns = patterns('',
    url(r'^logout/$', views.logout, name='logout'),
    url('^browserid/verify/', views.BrowserID.as_view(),
                              name='browserid_verify'),
    url(r'^register/$', views.register, name='register'))
