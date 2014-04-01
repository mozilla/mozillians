from django.conf.urls import patterns, url

from mozillians.groups.models import Group, Skill


urlpatterns = patterns(
    'mozillians.groups',
    url('^groups/$', 'views.index_groups', name='index_groups'),
    url('^skills/$', 'views.index_skills', name='index_skills'),
    url('^functional-areas/$', 'views.index_functional_areas',
        name='index_functional_areas'),

    url('^group_add/$', 'views.group_add_edit', name='group_add'),
    url('^group_edit/(?P<url>[-\'\w]+)/$', 'views.group_add_edit', name='group_edit'),
    url('^group_delete/(?P<url>[-\'\w]+)/$', 'views.group_delete', name='group_delete'),

    url('^group/(?P<url>[-\w]+)/$', 'views.show_group',
        {'template': 'groups/group.html'},
        name='show_group'),

    url('^skill/(?P<url>[-\w]+)/$', 'views.show_skill',
        {'template': 'groups/skill.html'},
        name='show_skill'),
    url('^skill/(?P<url>[-\w]+)/toggle/$', 'views.toggle_skill_subscription',
        name='toggle_skill_subscription'),

    url('^groups/search/$', 'views.search',
        dict(searched_object=Group), name='search_groups'),
    url('^skills/search/$', 'views.search',
        dict(searched_object=Skill), name='search_skills'),
    url('^group/(?P<group_pk>\d+)/join/$',
        'views.join_group', name='join_group'),
    url('^group/(?P<group_pk>\d+)/remove/(?P<user_pk>\d+)/$',
        'views.remove_member', name='remove_member'),
    url('^group/(?P<group_pk>\d+)/confirm/(?P<user_pk>\d+)/$',
        'views.confirm_member', name='confirm_member'),
)
