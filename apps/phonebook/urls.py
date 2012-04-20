from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template

from django.contrib import admin
admin.autodiscover()

from session_csrf import anonymous_csrf

from phonebook import views

urlpatterns = patterns('',
    url('^user/edit/$', views.edit_profile,
        name='profile.edit'),
    url('^register/edit/$', views.edit_profile, {'new_account': True},
        name='profile.new'),
    url('^confirm-delete$', views.confirm_delete,
        name='profile.delete_confirm'),
    url('^delete$', views.delete, name='profile.delete'),
    url('^opensearch.xml$', views.search_plugin, name='search_plugin'),
    url('^search$', views.search, name='search'),
    url('^vouch$', views.vouch, name='vouch'),

    url('^invite$', views.invite, name='invite'),
    url('^invited/(?P<id>\d+)$', views.invited, name='invited'),

    # Static pages need csrf for browserID post to work
    url('^about$', anonymous_csrf(direct_to_template),
        dict(template='phonebook/about.html'), name='about'),
    url('^confirm-register$', direct_to_template,
        {'template': 'phonebook/confirm_register.html'},
        name='confirm_register'),
    url('^$', anonymous_csrf(direct_to_template),
        {'template': 'phonebook/home.html'}, name='home'),
    url(r'^(?P<username>(u\/)?[\w.@+-]{1,30})$', views.profile, name='profile'),
)
