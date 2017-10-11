from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView

from mozillians.common.decorators import allow_public
from mozillians.phonebook.views import (PhonebookSearchView, VerifyIdentityView,
                                        VerifyIdentityCallbackView)


urlpatterns = patterns(
    'mozillians.phonebook',
    url(r'^$', 'views.home', name='home'),
    url(r'^login/$', 'views.login', name='login'),
    url(r'^logout/$', 'views.logout', name='logout'),
    url(r'^register/$', 'views.register', name='register'),
    # Use Auth0 to verify an identity
    url(r'^verify/identity/$', login_required(VerifyIdentityView.as_view()),
        name='verify_identity'),
    url(r'^verify/identity/callback/$', login_required(VerifyIdentityCallbackView.as_view()),
        name='verify_identity_callback'),

    url(r'^user/edit/$', 'views.edit_profile', name='profile_edit'),
    url(r'^u/(?P<username>[\w.@+-]+)/$', 'views.view_profile',
        name='profile_view'),
    url(r'^user/delete/email/(?P<email_pk>\d+)/$', 'views.delete_email',
        name='delete_email'),
    url(r'^user/primary/email/(?P<email_pk>\d+)/$', 'views.change_primary_email',
        name='change_primary_email'),
    url(r'^u/(?P<username>[\w.@+-]+)/vouch/$', 'views.vouch',
        name='profile_vouch'),
    url(r'^u/(?P<username>[\w.@+-]+)/unvouch/$', 'views.unvouch',
        name='profile_unvouch'),
    url(r'^confirm-delete/$', 'views.confirm_delete',
        name='profile_confirm_delete'),
    url(r'^delete/$', 'views.delete', name='profile_delete'),
    url(r'^opensearch.xml$', 'views.search_plugin', name='search_plugin'),
    url(r'^invite/$', 'views.invite', name='invite'),
    url(r'^invite/(?P<invite_pk>\d+)/delete/$', 'views.delete_invite', name='delete_invite'),
    url(r'^apikeys/$', 'views.apikeys', name='apikeys'),
    url(r'^apikey/(?P<api_pk>\d+)/delete/$', 'views.delete_apikey', name='apikey_delete'),
    # Haystack search
    url(r'^search/$', allow_public(PhonebookSearchView.as_view()),
        name='haystack_search'),
    url(r'^country/(?P<country>[A-Za-z0-9 \.\,]+)/$',
        PhonebookSearchView.as_view(), name='list_country'),
    url(r'^country/(?P<country>[A-Za-z0-9 \.\,]+)/city/(?P<city>.+)/$',
        PhonebookSearchView.as_view(), name='list_city'),
    url((r'^country/(?P<country>[A-Za-z0-9 \.\,]+)/'
         'region/(?P<region>.+)/city/(?P<city>.+)/$'),
        PhonebookSearchView.as_view(), name='list_region_city'),
    url(r'^country/(?P<country>[A-Za-z0-9 \.]+)/region/(?P<region>.+)/$',
        PhonebookSearchView.as_view(), name='list_region'),
    # Static pages need csrf for post to work
    url(r'^about/$',
        allow_public(TemplateView.as_view(template_name='phonebook/about.html')),
        name='about'),
    url(r'^about/dinomcvouch$',
        allow_public(TemplateView.as_view(template_name='phonebook/about-dinomcvouch.html')),
        name='about-dinomcvouch'),
    # CSP violation URL
    url(r'^capture-csp-violation$', 'views.capture_csp_violation', name='capture-csp-violation'),
)
