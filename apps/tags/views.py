from functools import wraps
from ldap import SIZELIMIT_EXCEEDED
from operator import attrgetter

import django.contrib.auth
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import (Http404, HttpResponse, HttpResponseRedirect,
                         HttpResponseForbidden)
from django.shortcuts import redirect, render
from django.utils import simplejson
from django.views.decorators.cache import cache_control, never_cache
from django.views.decorators.http import require_POST
from django.views.decorators.vary import vary_on_cookie

import commonware.log
from funfactory.urlresolvers import reverse
from tower import ugettext as _

from larper import UserSession, AdminSession, NO_SUCH_PERSON
from larper import MOZILLA_IRC_SERVICE_URI
from tags import forms
from tags.models import Tag

log = commonware.log.getLogger('m.tags')

@login_required
def list(request):
    """Lists all public tags (in use) on Mozillians."""
    data = {}
    return render(request, 'tags/index.html', data)


@login_required
@cache_control(must_revalidate=True, max_age=3600)
def search(request):
    """Simple wildcard search for a tag using a GET parameter."""
    data = dict(tags=[])
    search_term = request.GET.get('term')

    if search_term:
        data['tags'] = ([t.name for t in
                         Tag.objects.filter(name__istartswith=search_term,
                                            auto_complete=True, hidden=False)])

    if request.is_ajax():
        # Django's serializers wrapper module messes things up, but using
        # simplejson directly yields no problems.
        return HttpResponse(simplejson.dumps(data['tags']),
                            mimetype='application/json')
    else:
        return render(request, 'tags/index.html', data)
