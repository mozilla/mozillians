import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_control

import commonware.log

from .helpers import users_from_groups
from .models import Group

log = commonware.log.getLogger('m.groups')


@login_required
def index(request):
    """Lists all public groups (in use) on Mozillians."""
    all_groups = Group.objects.all().order_by('name')

    data = dict(groups=all_groups)
    return render(request, 'groups/index.html', data)


@login_required
def show(request, name):
    """List all users with this group."""
    group = get_object_or_404(Group, name=name)

    users = users_from_groups(request, group)

    data = dict(group=group, users=users)
    return render(request, 'groups/show.html', data)


@login_required
@cache_control(must_revalidate=True, max_age=3600)
def search(request):
    """Simple wildcard search for a group using a GET parameter."""
    data = dict(groups=[], search=True)
    search_term = request.GET.get('term')

    if search_term:
        data['groups'] = list(Group.objects
                                   .filter(name__istartswith=search_term,
                                           auto_complete=True)
                                   .values_list('name', flat=True))

    if request.is_ajax():
        return HttpResponse(json.dumps(data['groups']),
                            mimetype='application/json')
    else:
        return render(request, 'groups/index.html', data)
