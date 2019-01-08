import requests
import urlparse

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.utils.encoding import escape_uri_path
from django.views.decorators.cache import cache_control, never_cache

from mozillians.common.decorators import allow_public
from mozillians.dino_park.utils import UserAccessLevel, DinoErrorResponse


@never_cache
@login_required
def main(request):
    if not settings.DINO_PARK_ACTIVE:
        raise Http404()
    return render(request, 'dino_park/index.html', {})


@never_cache
def orgchart(request):
    """Internal routing to expose orgchart service."""
    scope = UserAccessLevel.get_privacy(request)
    if scope not in [UserAccessLevel.STAFF, UserAccessLevel.PRIVATE]:
        return DinoErrorResponse.get_error(DinoErrorResponse.PERMISSION_ERROR)

    url_parts = urlparse.ParseResult(
        scheme='http',
        netloc=settings.DINO_PARK_ORGCHART_SVC,
        path='/orgchart',
        params='',
        query='',
        fragment=''
    )
    url = urlparse.urlunparse(url_parts)
    resp = requests.get(url)
    resp.raise_for_status()
    return JsonResponse(resp.json(), safe=False)


@never_cache
def orgchart_get_by_username(request, path, username):
    """Internal routing to expose orgchart service by user_id."""
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = None

    # if there is a user and the user is not a staff member
    # then we don't need to search for a profile in orgchart
    if user and not user.userprofile.is_staff and path == 'trace':
        return JsonResponse(None, safe=False)

    scope = UserAccessLevel.get_privacy(request, user)
    if scope not in [UserAccessLevel.STAFF, UserAccessLevel.PRIVATE]:
        return DinoErrorResponse.get_error(DinoErrorResponse.PERMISSION_ERROR)

    url_parts = urlparse.ParseResult(
        scheme='http',
        netloc=settings.DINO_PARK_ORGCHART_SVC,
        path='/orgchart/{0}/{1}'.format(path, escape_uri_path(username)),
        params='',
        query='',
        fragment=''
    )
    url = urlparse.urlunparse(url_parts)
    resp = requests.get(url)
    return JsonResponse(resp.json(), safe=False)


@never_cache
@allow_public
def search_simple(request):
    """Internal routing to expose simple search."""
    scope = UserAccessLevel.get_privacy(request)
    url_parts = urlparse.ParseResult(
        scheme='http',
        netloc=settings.DINO_PARK_SEARCH_SVC,
        path='/search/simple/{}'.format(scope),
        params='',
        query=request.GET.urlencode(),
        fragment=''
    )
    url = urlparse.urlunparse(url_parts)
    resp = requests.get(url)
    resp.raise_for_status()
    return JsonResponse(resp.json(), safe=False)


@never_cache
@allow_public
def search_get_profile(request, username, scope=None):
    """Internal routing to expose search by user ID."""
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = None
    if not scope:
        scope = UserAccessLevel.get_privacy(request, user)
    url_parts = urlparse.ParseResult(
        scheme='http',
        netloc=settings.DINO_PARK_SEARCH_SVC,
        path='/search/get/{}/{}'.format(scope, escape_uri_path(username)),
        params='',
        query='',
        fragment=''
    )
    url = urlparse.urlunparse(url_parts)
    resp = requests.get(url)
    return JsonResponse(resp.json(), safe=False)


@allow_public
@cache_control(public=True, must_revalidate=True, max_age=3600 * 24 * 7)  # 1 week.
def search_plugin(request):
    """Render an OpenSearch Plugin."""
    # If DinoPark is running return the correct file
    if settings.DINO_PARK_ACTIVE:
        return render(request, 'dino_park/dinopark_opensearch.xml',
                      {'site_url': settings.SITE_URL},
                      content_type='application/opensearchdescription+xml')
    return render(request, 'phonebook/search_opensearch.xml',
                  content_type='application/opensearchdescription+xml')
