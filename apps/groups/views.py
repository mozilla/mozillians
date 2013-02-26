import json

from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, Paginator, PageNotAnInteger
from django.db.models import Count
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.http import require_POST

import commonware.log
from funfactory.urlresolvers import reverse

from apps.groups.models import Group, Skill
from apps.phonebook import forms
from apps.phonebook.views import vouch_required
from apps.users.models import UserProfile
from apps.users.tasks import update_basket_task

log = commonware.log.getLogger('m.groups')


@login_required
def index(request):
    """Lists all public groups (in use) on Mozillians."""
    paginator = Paginator(Group.objects.all(), forms.PAGINATION_LIMIT)

    page = request.GET.get('page')
    try:
        groups = paginator.page(page)
    except PageNotAnInteger:
        groups = paginator.page(1)
    except EmptyPage:
        groups = paginator.page(paginator.num_pages)

    data = dict(groups=groups)
    return render(request, 'groups/index.html', data)


@login_required
@cache_control(must_revalidate=True, max_age=3600)
def search(request, searched_object=Group):
    """Simple wildcard search for a group using a GET parameter."""
    data = dict(search=True)
    data['groups'] = list(searched_object.search(request.GET
                          .get('term')).values_list('name', flat=True))

    if request.is_ajax():
        return HttpResponse(json.dumps(data['groups']),
                            mimetype='application/json')

    if searched_object == Group:
        return render(request, 'groups/index.html', data)
    # Raise a 404 if this is a Skill page that isn't ajax
    raise Http404


@vouch_required
@never_cache
def show(request, url):
    """ List all users with this group."""
    group = get_object_or_404(Group, url=url)
    limit = forms.PAGINATION_LIMIT

    in_group = (group.userprofile_set
                .filter(id=request.user.userprofile.id).exists())
    profiles = group.userprofile_set.exclude(full_name='')
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

    d = dict(people=people,
             group=group,
             in_group=in_group,
             limit=limit,
             show_pagination=show_pagination,
             num_pages=num_pages)

    if group.steward:
        # Get the 15 most globally popular skills that appear in the group
        skills = [s.name for s in (Skill.objects
                                   .filter(userprofile__group__id=group.id)
                                   .annotate(users=Count('userprofile'))
                                   .order_by('users'))][:15]
        d.update(skills=skills)
        d.update(irc_channels=group.irc_channel.split(' '))
        d.update(members=UserProfile.objects.filter(groups=group).count())

    if request.is_ajax():
        return render(request, 'search_ajax.html', d)

    return render(request, 'groups/group.html', d)


@require_POST
@vouch_required
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
