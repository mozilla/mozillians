from django.shortcuts import render
from django.views.decorators.cache import never_cache

from mozillians.common.decorators import allow_public


@never_cache
@allow_public
def main(request):
    return render(request, 'dino_park/index.html', {})
