import json

from django.conf import settings
from django.core.paginator import EmptyPage, Paginator, PageNotAnInteger
from django.db.models import Count
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.http import require_POST

from funfactory.urlresolvers import reverse

from mozillians.common.decorators import allow_unvouched
from mozillians.groups.models import Group, Skill
from mozillians.groups.forms import SortForm
from mozillians.users.tasks import update_basket_task


def _list_groups(request, template, query):
    """Lists groups from given query."""

    sort_form = SortForm(request.GET)
    show_pagination = False

    if sort_form.is_valid():
        query = query.order_by(sort_form.cleaned_data['sort'], 'name')
    else:
        query = query.order_by('name')

    paginator = Paginator(query, settings.ITEMS_PER_PAGE)

    page = request.GET.get('page', 1)
    try:
        groups = paginator.page(page)
    except PageNotAnInteger:
        groups = paginator.page(1)
    except EmptyPage:
        groups = paginator.page(paginator.num_pages)

    if paginator.count > settings.ITEMS_PER_PAGE:
        show_pagination = True

    data = dict(groups=groups, page=page, sort_form=sort_form, show_pagination=show_pagination)
    return render(request, template, data)


def index_groups(request):
    """Lists all public groups (in use) on Mozillians."""
    query = (Group.objects.filter(members__is_vouched=True)
             .annotate(num_members=Count('members')))
    template = 'groups/index_groups.html'
    return _list_groups(request, template, query)


def index_skills(request):
    """Lists all public groups (in use) on Mozillians."""
    query = (Skill.objects.filter(members__is_vouched=True)
             .annotate(num_members=Count('members')))
    template = 'groups/index_skills.html'
    return _list_groups(request, template, query)


def index_functional_areas(request):
    """Lists all curated groups."""
    query = Group.get_curated()
    template = 'groups/index_areas.html'
    return _list_groups(request, template, query)


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

    return HttpResponseBadRequest()


@never_cache
def show(request, url, alias_model, template):
    """List all vouched users with this group."""
    group_alias = get_object_or_404(alias_model, url=url)
    if group_alias.alias.url != url:
        return redirect('groups:show_group', url=group_alias.alias.url)

    group = group_alias.alias
    in_group = group.members.filter(user=request.user).exists()
    profiles = group.members.vouched()

    page = request.GET.get('page', 1)
    paginator = Paginator(profiles, settings.ITEMS_PER_PAGE)

    try:
        people = paginator.page(page)
    except PageNotAnInteger:
        people = paginator.page(1)
    except EmptyPage:
        people = paginator.page(paginator.num_pages)

    show_pagination = paginator.count > settings.ITEMS_PER_PAGE

    profile = request.user.userprofile
    hide_leave_group_button = (hasattr(group, 'steward')
        and (profile == group.steward))
    data = dict(people=people,
                group=group,
                in_group=in_group,
                show_pagination=show_pagination,
                hide_leave_group_button=hide_leave_group_button)

    if isinstance(group, Group) and group.steward:
        """ Get the most globally popular skills that appear in the group
            Sort them with most members first
        """
        skills = (Skill.objects
                  .filter(members__in=profiles)
                  .annotate(no_users=Count('members'))
                  .order_by('-no_users'))
        data.update(skills=skills)
        data.update(irc_channels=group.irc_channel.split(' '))
        data.update(members=profiles.count())

    return render(request, template, data)


@require_POST
def toggle_group_subscription(request, url):
    """Toggle the current user's membership of a group."""
    group = get_object_or_404(Group, url=url)
    profile = request.user.userprofile

    # We don't operate on system groups using this view.
    if not group.system:
        if profile.groups.filter(id=group.id).exists():
            profile.groups.remove(group)
        else:
            profile.groups.add(group)
        update_basket_task.delay(profile.id)

    return redirect(reverse('groups:show_group', args=[group.url]))


@require_POST
def toggle_skill_subscription(request, url):
    """Toggle the current user's membership of a group."""
    skill = get_object_or_404(Skill, url=url)
    profile = request.user.userprofile

    if profile.skills.filter(id=skill.id).exists():
        profile.skills.remove(skill)
    else:
        profile.skills.add(skill)

    return redirect(reverse('groups:show_skill', args=[skill.url]))
