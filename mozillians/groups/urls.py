from django.conf.urls import patterns, url

from mozillians.groups.models import Group, GroupAlias, Skill, SkillAlias


urlpatterns = patterns(
    'mozillians.groups',
    url('^functional-areas/$', 'views.index_functional_areas',
        name='index_functional_areas'),

    url('^groups/$', 'views.index_groups', name='index_groups'),
    url('^groups/add/$', 'views.group_add_edit', name='group_add'),
    url('^group/(?P<url>[-\w]+)/edit/$', 'views.group_add_edit', name='group_edit'),
    url('^group/(?P<url>[-\w]+)/delete/$', 'views.group_delete', name='group_delete'),
    url('^group/(?P<url>[-\w]+)/$', 'views.show',
        {'alias_model': GroupAlias, 'template': 'groups/group.html'},
        name='show_group'),
    url('^groups/search/$', 'views.search',
        dict(searched_object=Group), name='search_groups'),
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
    url('^skills/search/$', 'views.search',
        dict(searched_object=Skill), name='search_skills'),
    url('^group/(?P<url>[-\w]+)/geodata.json$', 'views.geodata',
        {'alias_model': GroupAlias}, name='show_geodata'),
)
