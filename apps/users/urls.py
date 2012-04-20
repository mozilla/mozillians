from django.conf.urls.defaults import include, patterns, url
from django.contrib.auth import views as auth_views
from django.views.generic.simple import redirect_to

from jinjautils import jinja_for_django
from tastypie.api import Api

from users import api, views

# So we can use the contrib logic for password resets, etc.
auth_views.render_to_response = jinja_for_django

v1_api = Api(api_name='v1')
v1_api.register(api.UserProfileResource())


urlpatterns = patterns('',
    url(r'^logout$', views.logout, name='logout'),
    url(r'^confirm$', redirect_to, dict(url='/', name='home')),
    url('^browserid/verify/', views.Browserid.as_view(),
                              name='browserid_verify'),
    url(r'^api/', include(v1_api.urls)),

    # This sucks: we should not have to do this, but a lot of people/libraries/
    # existing code is looking for this view.
    url(r'^login$', redirect_to, dict(url='/', name='home'), name='login'),
    url(r'^register$', views.register, name='register'),
    # TODO: remove in 1.4 release, legacy url sent in emails
    url(r'^password_reset_confirm/'
         '(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-'
         '[0-9A-Za-z]{1,20})/$',
        redirect_to, dict(url='/', name='password_reset_confirm')),
)
