from django.conf.urls.defaults import patterns, url

from django.contrib.auth import views as auth_views, forms as auth_forms

from jinjautils import jinja_for_django
from session_csrf import anonymous_csrf

from . import views

# So we can use the contrib logic for password resets, etc.
auth_views.render_to_response = jinja_for_django


urlpatterns = patterns('',
    url(r'^login', anonymous_csrf(auth_views.login), name='login'),
    url(r'^logout', auth_views.logout, dict(redirect_field_name='next'),
        name='logout'),
    url(r'^register', views.register, name='register'),
)
