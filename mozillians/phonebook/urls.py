from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template

from mozillians.common.decorators import allow_public


urlpatterns = patterns(
    'mozillians.phonebook',
    url(r'^$', 'views.home', name='home'),
    url(r'^login/$', 'views.login', name='login'),
    url(r'^logout/$', 'views.logout', name='logout'),
    url(r'^register/$', 'views.register', name='register'),
    url(r'^user/edit/$', 'views.edit_profile', name='profile_edit'),
    url(r'^u/(?P<username>[\w.@+-]+)/$', 'views.view_profile',
        name='profile_view'),
    url(r'^confirm-delete/$', 'views.confirm_delete',
        name='profile_confirm_delete'),
    url(r'^delete/$', 'views.delete', name='profile_delete'),
    url(r'^opensearch.xml$', 'views.search_plugin', name='search_plugin'),
    url(r'^search/$', 'views.search', name='search'),
    url(r'^vouch/$', 'views.vouch', name='vouch'),
    url(r'^invite/$', 'views.invite', name='invite'),
    url(r'^invite/(?P<invite_pk>\d+)/delete/$', 'views.delete_invite', name='delete_invite'),
    url(r'^country/(?P<country>[A-Za-z]+)/$',
        'views.list_mozillians_in_location', name='list_country'),
    url(r'^country/(?P<country>[A-Za-z]+)/city/(?P<city>.+)/$',
        'views.list_mozillians_in_location', name='list_city'),
    url((r'^country/(?P<country>[A-Za-z]+)/'
         'region/(?P<region>.+)/city/(?P<city>.+)/$'),
        'views.list_mozillians_in_location', name='list_region_city'),
    url(r'^country/(?P<country>[A-Za-z]+)/region/(?P<region>.+)/$',
        'views.list_mozillians_in_location', name='list_region'),


    # Static pages need csrf for browserID post to work
    url(r'^about/$', allow_public(direct_to_template),
        {'template': 'phonebook/about.html'}, name='about'),
)
