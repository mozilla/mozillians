from django.conf import settings
from django.shortcuts import redirect
from django.views.static import serve

from mozillians.common.decorators import allow_public
from mozillians.common.helpers import absolutify


@allow_public
def humans(request):
    return redirect(absolutify(settings.HUMANSTXT_URL))


@allow_public
def contribute_view(request):
    """Generate a contribute.json"""
    return serve(request, 'contribute.json', document_root=settings.ROOT)
