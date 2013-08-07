from django.conf.urls.defaults import patterns, url

from mozillians.groups.models import Group, Skill, Language


urlpatterns = patterns('mozillians.groups',
    url('^groups/$', 'views.index', name='index'),
    url('^group/(?P<url>[-\w]+)/$', 'views.show', name='show'),

    url('^functional-areas/$', 'views.index_functional_areas',
        name='index_functional_areas'),
    url('^group/(?P<url>[-\w]+)/toggle/$', 'views.toggle_subscription',
        name='toggle_subscription'),
    url('^groups/search/$', 'views.search',
        dict(searched_object=Group), name='search_groups'),
    url('^skills/search/$', 'views.search',
        dict(searched_object=Skill), name='search_skills'),
    url('^languages/search/$', 'views.search',
        dict(searched_object=Language), name='search_languages'),
)
