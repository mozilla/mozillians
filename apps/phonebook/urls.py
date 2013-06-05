from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template

from apps.common.decorators import allow_public

import views

urlpatterns = patterns('',
    url('^$', views.home, name='home'),
    url('^user/edit/$', views.edit_profile,
        name='profile.edit'),
    url('^confirm-delete/$', views.confirm_delete,
        name='profile.delete_confirm'),
    url('^messenger-add/$', views.messenger_add,
        name='messenger_add'),
    url('^messenger-remove/$', views.messenger_remove,
        name='messenger_remove'),
    url('^delete/$', views.delete, name='profile.delete'),
    url('^opensearch.xml$', views.search_plugin, name='search_plugin'),
    url('^search/$', views.search, name='search'),
    url('^vouch/$', views.vouch, name='vouch'),
    url('^invite/$', views.invite, name='invite'),
    url('^country/(?P<country>[A-Za-z]+)/$', views.list_mozillians_in_location,
        name='list_country'),
    url('^country/(?P<country>[A-Za-z]+)/city/(?P<city>.+)/$',
        views.list_mozillians_in_location, name='list_city'),
    url(('^country/(?P<country>[A-Za-z]+)/'
         'region/(?P<region>.+)/city/(?P<city>.+)/$'),
        views.list_mozillians_in_location, name='list_region_city'),
    url('^country/(?P<country>[A-Za-z]+)/region/(?P<region>.+)/$',
        views.list_mozillians_in_location, name='list_region'),


    # Static pages need csrf for browserID post to work
    url('^about/$', allow_public(direct_to_template),
        {'template': 'phonebook/about.html'}, name='about'),
    url(r'^u/(?P<username>[\w.@+-]+)/$',
        views.view_profile, name='profile'),
)
