from django.conf.urls.defaults import patterns, url

import views
from models import Group, Skill, Language

urlpatterns = patterns('',
    url('^groups/$', views.index, name='group_index'),
    url('^group/(?P<url>[-\w]+)/$', views.show, name='group'),
    url('^group/(?P<url>[-\w]+)/toggle/$', views.toggle, name='group_toggle'),
    url('^groups/search/$', views.search,
        dict(searched_object=Group), name='group_search'),
    url('^skills/search/$', views.search,
        dict(searched_object=Skill), name='skill_search'),
    url('^languages/search/$', views.search,
        dict(searched_object=Language), name='language_search'),
)
