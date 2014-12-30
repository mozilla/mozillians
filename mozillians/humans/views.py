from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render

from mozillians.common.decorators import allow_public
from mozillians.common.helpers import absolutify


@allow_public
def humans(request):
    return redirect(absolutify(settings.HUMANSTXT_URL))


@allow_public
def contribute_view(request):
    """Generate a contribute.json"""
    template = render(request, 'humans/contribute.json')
    return HttpResponse(template, mimetype='application/json')
