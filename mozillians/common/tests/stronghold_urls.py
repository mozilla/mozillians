from django.conf import settings
from django.conf.urls import url
from django.http import HttpResponse
from mozillians.common.decorators import allow_public, allow_unvouched

from mozillians.urls import urlpatterns


def vouched(request):
    return HttpResponse('Hi!')


@allow_unvouched
def unvouched(request):
    return HttpResponse('Hi!')


@allow_public
def public(request):
    return HttpResponse('Hi!')


urlpatterns += [
    url(r'^vouched/$', vouched, name='vouched'),
    url(r'^unvouched/$', unvouched, name='unvouched'),
    url(r'^public/$', public, name='public'),
    url(r'^excepted/$', vouched, name='excepted')
]


settings.STRONGHOLD_EXCEPTIONS += ['^/en-US/excepted/$']
