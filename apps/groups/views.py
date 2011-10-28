import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_control

import commonware.log

from larper import UserSession
from .models import Group

log = commonware.log.getLogger('m.groups')


@login_required
def index(request):
    """Lists all public groups (in use) on Mozillians."""
    all_groups = Group.objects.filter(system=False).order_by('name')

    data = dict(groups=all_groups)
    return render(request, 'groups/index.html', data)


@login_required
def show(request, name):
    """List all users with this group."""
    group = get_object_or_404(Group, name=name)

    profiles = group.userprofile_set.all()
    users = User.objects.filter(id__in=[p.user_id for p in profiles])
    ldap = UserSession.connect(request)

    ldap_users = []
    for u in users:
        # We have to walk this so we don't hit LDAP's HARD LIMIT.
        ldap_users.append(ldap.search_by_email(u.email)[0])

    data = dict(group=group, users=ldap_users)
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
                                           auto_complete=True,
                                           system=False)
                                   .values_list('name', flat=True))

    if request.is_ajax():
        return HttpResponse(json.dumps(data['groups']),
                            mimetype='application/json')
    else:
        return render(request, 'groups/index.html', data)
