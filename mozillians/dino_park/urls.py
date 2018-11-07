from django.conf.urls import url

from mozillians.dino_park import views as dino_park_views


app_name = 'dino_park'
urlpatterns = [
    url('^api/v3/orgchart/$',
        dino_park_views.orgchart, name='dino_park_orgchart'),
    url('^api/v3/orgchart/(?P<path>related|trace)/(?P<user_id>\w+)/$',
        dino_park_views.orgchart_get_by_id, name='dino_park_orgchart_get_by_id'),
    url('^api/v3/search/simple/(?P<query>.+)/$',
        dino_park_views.search_simple, name='dino_park_search_simple'),
    url('^api/v3/search/get/(?P<user_id>\w+)/$',
        dino_park_views.search_get_profile, name='dino_park_search_get_profile'),
    url('^beta/.*$', dino_park_views.main, name='dino_park_main'),
]
