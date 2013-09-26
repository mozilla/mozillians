from django.conf.urls.defaults import patterns, url

from mozillians.groups.models import Group, GroupAlias, Skill, SkillAlias, Language


urlpatterns = patterns(
    'mozillians.groups',
    url('^groups/$', 'views.index_groups', name='index_groups'),
    url('^skills/$', 'views.index_skills', name='index_skills'),
    url('^functional-areas/$', 'views.index_functional_areas',
        name='index_functional_areas'),

    url('^group/(?P<url>[-\w]+)/$', 'views.show',
        {'alias_model': GroupAlias, 'template': 'groups/group.html'},
        name='show_group'),
    url('^group/(?P<url>[-\w]+)/toggle/$', 'views.toggle_group_subscription',
        name='toggle_group_subscription'),

    url('^skill/(?P<url>[-\w]+)/$', 'views.show',
        {'alias_model': SkillAlias, 'template': 'groups/skill.html'},
        name='show_skill'),
    url('^skill/(?P<url>[-\w]+)/toggle/$', 'views.toggle_skill_subscription',
        name='toggle_skill_subscription'),

    url('^groups/search/$', 'views.search',
        dict(searched_object=Group), name='search_groups'),
    url('^skills/search/$', 'views.search',
        dict(searched_object=Skill), name='search_skills'),
    url('^languages/search/$', 'views.search',
        dict(searched_object=Language), name='search_languages'),
)
