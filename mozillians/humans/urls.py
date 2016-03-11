from django.conf.urls import url

from mozillians.humans import views


urlpatterns = [
    url(r'^humans.txt$', views.humans, name='humans'),
    url(r'^contribute.json$', views.contribute_view, name='contribute-view')
]
