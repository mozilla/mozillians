from django.conf.urls import url

from mozillians.dino_park import views as dino_park_views


app_name = 'dino_park'
urlpatterns = [
    url('^beta/.*$', dino_park_views.main, name='dino_park_main'),
]
