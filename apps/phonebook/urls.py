from django.conf import settings
from django.conf.urls.defaults import patterns, url
from django.views.generic.simple import direct_to_template

from django.contrib import admin
admin.autodiscover()

from phonebook import views

urlpatterns = patterns('',
    url('^user/edit/$', views.edit_profile,
        name='phonebook.edit_profile'),
    url('^register/edit/$', views.edit_new_profile,
        name='phonebook.edit_new_profile'),
    url('^confirm-delete$', views.confirm_delete, name='confirm_delete'),
    url('^delete$', views.delete, name='phonebook.delete_profile'),
    url('^opensearch.xml$', views.search_plugin, name='phonebook.search_plugin'),
    url('^search$', views.search, name='phonebook.search'),
    url('^vouch$', views.vouch, name='phonebook.vouch'),

    url('^invite$', views.invite, name='invite'),
    url('^invited/(?P<id>\d+)$', views.invited, name='invited'),

    # Static pages
    url('^about$', direct_to_template, {'template': 'phonebook/about.html'},
        name='about'),
    url('^confirm-register$', direct_to_template,
        {'template': 'phonebook/confirm_register.html'},
        name='confirm_register'),
    url('^$', direct_to_template, {'template': 'phonebook/home.html'},
        name='home'),

    url(r'^(?P<username>.+)$', views.profile, name='profile'),
)
