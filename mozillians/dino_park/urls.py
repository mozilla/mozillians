from django.conf.urls import url

from mozillians.dino_park import views as dino_park_views


app_name = 'dino_park'
urlpatterns = [
    url('^api/v3/orgchart/$',
        dino_park_views.orgchart, name='dino_park_orgchart'),
    url('^api/v3/orgchart/(?P<path>related|trace)/(?P<username>.+)/$',
        dino_park_views.orgchart_get_by_username, name='dino_park_orgchart_get_by_username'),
    url('^api/v3/search/simple/$',
        dino_park_views.search_simple, name='dino_park_search_simple'),
    url('^api/v3/search/get/(?P<username>.+)/$',
        dino_park_views.search_get_profile, name='dino_park_search_get_profile'),
    url(r'^opensearch.xml$', dino_park_views.search_plugin, name='search_plugin'),
    url('^beta/.*$', dino_park_views.main, name='dino_park_main'),
]
