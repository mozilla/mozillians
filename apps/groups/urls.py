from django.conf.urls.defaults import patterns, url

from django.contrib import admin
admin.autodiscover()

from . import views
from groups.models import Group, Skill

urlpatterns = patterns('',
    url('^groups$', views.index, name='group_index'),
    url('^groups/search$', views.search, dict(searched_object=Group), name='group_search'),
    url('^skills/search$', views.search, dict(searched_object=Skill), name='skill_search'),
    url('^groups/(?P<slug>[\w-]{1,50})$', views.show, name='group'),
    url('^groups/(?P<slug>[\w-]{1,50})/toggle$',
        views.toggle, name='group_toggle'),
)
