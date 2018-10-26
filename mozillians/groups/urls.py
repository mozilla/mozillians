from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from dal import autocomplete

from mozillians.groups.models import Group, GroupAlias, Skill, SkillAlias
from mozillians.groups import views as group_views
from mozillians.users.views import CuratorsAutocomplete


OPTIONAL_MEMBERSHIP_STATUS = r'(?:/(?P<status>[-\w]+))?'


app_name = 'groups'
urlpatterns = [
    url(r'^functional-areas/$', group_views.index_functional_areas, name='index_functional_areas'),
    url(r'^groups/$', group_views.index_groups, name='index_groups'),
    url(r'^groups/add/$', group_views.index_groups, name='group_add'),
    url(r'^group/(?P<url>[-\w]+)/edit/$', group_views.group_edit, name='group_edit'),
    url(r'^group/(?P<url>[-\w]+)/delete/$', group_views.group_delete, name='group_delete'),
    url(r'^group/(?P<url>[-\w]+)/terms/$', group_views.review_terms, name='review_terms'),
    url(r'^group/(?P<url>[-\w]+)/$', group_views.show,
        {'alias_model': GroupAlias, 'template': 'groups/group.html'},
        name='show_group'),
    url(r'^group/(?P<url>[-\w]+)/force-invalidate/$', group_views.force_group_invalidation,
        {'alias_model': GroupAlias, 'template': 'groups/group.html'},
        name='force_group_invalidation'),
    url(r'^group/(?P<url>[-\w]+)/join/$', group_views.join_group, name='join_group'),
    url(r'^group/(?P<url>[-\w]+)/remove/(?P<user_pk>\d+){0}/$'.format(OPTIONAL_MEMBERSHIP_STATUS),
        group_views.remove_member, name='remove_member'),
    url(r'^group/(?P<url>[-\w]+)/confirm/(?P<user_pk>\d+)/$',
        group_views.confirm_member, name='confirm_member'),

    url(r'^skills/$', group_views.index_skills, name='index_skills'),
    url(r'^skill/(?P<url>[-\w]+)/$', group_views.show,
        {'alias_model': SkillAlias, 'template': 'groups/skill.html'},
        name='show_skill'),
    url(r'^skill/(?P<url>[-\w]+)/toggle/$', group_views.toggle_skill_subscription,
        name='toggle_skill_subscription'),
    # Django-autocomplete-light urls
    url(r'group-autocomplete/$',
        login_required(autocomplete.Select2QuerySetView.as_view(model=Group)),
        name='group-autocomplete'),
    url('^groups/search/$', group_views.search,
        dict(searched_object=Group), name='search_groups'),
    url(r'^skills-autocomplete/$',
        login_required(group_views.SkillsAutocomplete.as_view(model=Skill, create_field='name')),
        name='skills-autocomplete'),
    url(r'^curators/autocomplete/$', CuratorsAutocomplete.as_view(), name='curators-autocomplete'),
    # Invites section
    url(r'^groups/invite/(?P<invite_pk>\d+)/delete/$', group_views.delete_invite,
        name='delete_invite'),
    url(r'^groups/invite/(?P<invite_pk>\d+)/notify/$', group_views.send_invitation_email,
        name='send_invitation_email'),
    url(r'^groups/(?P<invite_pk>\d+)/(?P<action>accept|reject)/$',
        group_views.accept_reject_invitation, name='accept_reject_invitation'),
    # Testing
    url(r'^groups/membership_renewal_notification', group_views.membership_renewal_notification,
        name='membership_renewal_notification')
]
