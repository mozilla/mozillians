from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from dal import autocomplete

from mozillians.groups.models import Group, GroupAlias, SkillAlias
from mozillians.groups.views import SkillsAutocomplete
from mozillians.users.views import CuratorsAutocomplete


urlpatterns = patterns(
    'mozillians.groups',
    url('^functional-areas/$', 'views.index_functional_areas',
        name='index_functional_areas'),

    url('^groups/$', 'views.index_groups', name='index_groups'),
    url('^groups/add/$', 'views.index_groups', name='group_add'),
    url('^group/(?P<url>[-\w]+)/edit/$', 'views.group_edit', name='group_edit'),
    url('^group/(?P<url>[-\w]+)/delete/$', 'views.group_delete', name='group_delete'),
    url('^group/(?P<url>[-\w]+)/terms/$', 'views.review_terms', name='review_terms'),
    url('^group/(?P<url>[-\w]+)/$', 'views.show',
        {'alias_model': GroupAlias, 'template': 'groups/group.html'},
        name='show_group'),
    url('^group/(?P<url>[-\w]+)/join/$',
        'views.join_group', name='join_group'),
    url('^group/(?P<url>[-\w]+)/remove/(?P<user_pk>\d+)/$',
        'views.remove_member', name='remove_member'),
    url('^group/(?P<url>[-\w]+)/confirm/(?P<user_pk>\d+)/$',
        'views.confirm_member', name='confirm_member'),

    url('^skills/$', 'views.index_skills', name='index_skills'),
    url('^skill/(?P<url>[-\w]+)/$', 'views.show',
        {'alias_model': SkillAlias, 'template': 'groups/skill.html'},
        name='show_skill'),
    url('^skill/(?P<url>[-\w]+)/toggle/$', 'views.toggle_skill_subscription',
        name='toggle_skill_subscription'),
    # Django-autocomplete-light urls
    url('group-autocomplete/$',
        login_required(autocomplete.Select2QuerySetView.as_view(model=Group)),
        name='group-autocomplete'),
    url('^groups/search/$', 'views.search',
        dict(searched_object=Group), name='search_groups'),
    url('^skills/autocomplete/$', login_required(SkillsAutocomplete.as_view()),
        name='skills-autocomplete'),
    url('^curators/autocomplete/$', CuratorsAutocomplete.as_view(),
        name='curators-autocomplete'),
    # Invites section
    url('^groups/invite/(?P<invite_pk>\d+)/delete/$', 'views.delete_invite', name='delete_invite'),
    url('^groups/invite/(?P<invite_pk>\d+)/notify/$', 'views.send_invitation_email',
        name='send_invitation_email'),
    url('^groups/(?P<invite_pk>\d+)/(?P<action>accept|reject)/$',
        'views.accept_reject_invitation', name='accept_reject_invitation'),
)
