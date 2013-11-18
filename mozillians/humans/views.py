from django.conf import settings
from django.shortcuts import redirect

from mozillians.common.decorators import allow_public
from mozillians.common.helpers import absolutify


@allow_public
def humans(request):
    return redirect(absolutify(settings.HUMANSTXT_URL))
