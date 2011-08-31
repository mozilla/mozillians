from django.conf.urls.defaults import patterns, url

from django.contrib.auth import views as auth_views

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

    url(r'^password_change', views.password_change,
        name='password_change'),
    url(r'^password_change_done', auth_views.password_change_done,
        name='password_change_done'),

    url(r'^password_reset$', views.password_reset,
        name='password_reset'),

    url(r'^password_reset_check_mail$', views.password_reset_check_mail,
        name='password_reset_check_mail'),

    url(r'^password_reset_confirm/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
     views.password_reset_confirm,
     name='password_reset_confirm'),

    url(r'^password_reset_complete$', auth_views.password_reset_complete,
        name='password_reset_complete'),

)
