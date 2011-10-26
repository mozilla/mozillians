from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import simplejson
from django.views.decorators.cache import cache_control

import commonware.log

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
