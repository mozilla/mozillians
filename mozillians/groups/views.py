import json

from django.core.paginator import EmptyPage, Paginator, PageNotAnInteger
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.http import require_POST

import commonware.log
from funfactory.urlresolvers import reverse

from mozillians.common.decorators import allow_unvouched
from mozillians.groups.models import Group, Skill
from mozillians.groups.forms import SortForm
from mozillians.phonebook import forms
from mozillians.users.tasks import update_basket_task


log = commonware.log.getLogger('m.groups')


def list_groups(request, template, query):
    """Lists groups from given query."""
    sort_form = SortForm(request.GET)
    if sort_form.is_valid():
        query = query.order_by(sort_form.cleaned_data['sort'], 'name')
    else:
        query = query.order_by('name')

    paginator = Paginator(query, forms.PAGINATION_LIMIT_LARGE)

    page = request.GET.get('page')
    try:
        groups = paginator.page(page)
    except PageNotAnInteger:
        groups = paginator.page(1)
    except EmptyPage:
        groups = paginator.page(paginator.num_pages)

    data = dict(groups=groups, page=page, sort_form=sort_form)
    return render(request, template, data)


def index(request):
    """Lists all public groups (in use) on Mozillians."""
    query = (Group.objects.filter(members__is_vouched=True)
             .annotate(num_members=Count('members')))
    template = 'groups/index.html'
    return list_groups(request, template, query)


def index_functional_areas(request):
    """Lists all curated groups."""
    query = Group.get_curated()
    template = 'groups/areas.html'
    return list_groups(request, template, query)


@allow_unvouched
@cache_control(must_revalidate=True, max_age=3600)
def search(request, searched_object=Group):
    """Simple wildcard search for a group using a GET parameter.

    Used for group/skill/language auto-completion.

    """
    term = request.GET.get('term', None)
    if request.is_ajax() and term:
        groups = searched_object.search(term).values_list('name', flat=True)
        return HttpResponse(json.dumps(list(groups)),
                            mimetype='application/json')

    return redirect('home')


@never_cache
def show(request, url):
    """List all vouched users with this group."""
    group_alias = get_object_or_404(GroupAlias, url=url)
    if group_alias.alias.url != url:
        return redirect('groups:show', url=group_alias.alias.url)

    group = group_alias.alias
    limit = forms.PAGINATION_LIMIT
    in_group = (group.members.filter(user=request.user).exists())
    profiles = group.members.vouched()
    page = request.GET.get('page', 1)
    paginator = Paginator(profiles, limit)
    people = []
    try:
        people = paginator.page(page)
    except PageNotAnInteger:
        people = paginator.page(1)
    except EmptyPage:
        people = paginator.page(paginator.num_pages)

    show_pagination = False
    num_pages = 0
    if paginator.count > forms.PAGINATION_LIMIT:
        show_pagination = True
        num_pages = len(people.paginator.page_range)

    data = dict(people=people,
                group=group,
                in_group=in_group,
                limit=limit,
                show_pagination=show_pagination,
                num_pages=num_pages)

    if group.steward:
        # Get the 15 most globally popular skills that appear in the group
        skills = (Skill.objects
                  .filter(members__in=profiles)
                  .annotate(no_users=Count('members'))
                  .order_by('no_users'))
        data.update(skills=skills)
        data.update(irc_channels=group.irc_channel.split(' '))
        data.update(members=profiles.count())

    if request.is_ajax():
        return render(request, 'search_ajax.html', data)

    return render(request, 'groups/group.html', data)


@require_POST
def toggle(request, url):
    """Toggle the current user's membership of a group."""
    group = get_object_or_404(Group, url=url)
    profile = request.user.get_profile()

    # We don't operate on system groups using this view.
    if not group.system:
        if profile.groups.filter(id=group.id).exists():
            profile.groups.remove(group)
        else:
            profile.groups.add(group)

        update_basket_task.delay(profile.id)

    return redirect(reverse('group', args=[group.url]))
