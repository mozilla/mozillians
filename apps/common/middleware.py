import re
from contextlib import contextmanager
from django.conf import settings
from django.core.urlresolvers import is_valid_path, reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.encoding import iri_to_uri
from django.shortcuts import redirect
from tower import ugettext as _

from apps.groups.models import Group, GroupAlias

LOGIN_MESSAGE = _('You must be logged in to continue.')
GET_VOUCHED_MESSAGE = _('You must be vouched to continue.')


class RegisterMiddleware(object):
    """Redirect authenticated users with incomplete profile to register view."""
    def process_request(self, request):
        user = request.user
        path = request.path
        allow_urls = (r'^/[\w-]+{0}'.format(reverse('logout')),
                      r'^/[\w-]+{0}'.format(reverse('browserid_logout')),
                      r'^/[\w-]+{0}'.format(reverse('register')),
                      settings.MEDIA_URL if settings.DEBUG else '')

        if (user.is_authenticated() and not user.userprofile.is_complete
            and not filter(lambda url: re.match(url, path), allow_urls)):
            messages.warning(request, _('Please complete registration '
                                        'before proceeding.'))
            return redirect('register')


class StrongholdMiddleware(object):
    """Keep unvouched users out, unless explicitly allowed in.

    Inspired by https://github.com/mgrouchy/django-stronghold/

    """

    def __init__(self):
        self.exceptions = getattr(settings, 'STRONGHOLD_EXCEPTIONS', [])

    def process_view(self, request, view_func, view_args, view_kwargs):
        for view_url in self.exceptions:
            if re.match(view_url, request.path):
                return None

        allow_public = getattr(view_func, '_allow_public', None)
        if allow_public:
            return None

        if not request.user.is_authenticated():
            messages.warning(request, LOGIN_MESSAGE)
            return login_required(view_func)(request, *view_args,
                                             **view_kwargs)

        if request.user.userprofile.is_vouched:
            return None

        allow_unvouched = getattr(view_func, '_allow_unvouched', None)
        if allow_unvouched:
            return None

        messages.error(request, GET_VOUCHED_MESSAGE)
        return redirect('home')


class UsernameRedirectionMiddleware(object):
    """
    Redirect requests for user profiles from /<username> to
    /u/<username> to avoid breaking profile urls with the new url
    schema.

    """

    def process_response(self, request, response):
        if (response.status_code == 404
            and not request.path_info.startswith('/u/')
            and not is_valid_path(request.path_info)
            and User.objects.filter(
                username__iexact=request.path_info[1:].strip('/')).exists()
            and request.user.is_authenticated()
            and request.user.userprofile.is_vouched):

            newurl = '/u' + request.path_info
            if request.GET:
                with safe_query_string(request):
                    newurl += '?' + request.META['QUERY_STRING']
            return HttpResponseRedirect(newurl)
        return response


class OldGroupRedirectionMiddleware(object):
    """
    Redirect requests for groups from /group/<id>-<url> to
    /group/<url> to avoid breaking group urls with the new url
    schema.

    """

    def process_response(self, request, response):
        group_url = re.match('^/group/(?P<id>\d+)-(?P<url>[-\w]+)/$',
                             request.path_info)
        if (response.status_code == 404
            and group_url
            and (Group.objects.filter(url=group_url.group('url')).exists())):

            newurl = reverse('group', args=[group_url.group('url')])
            if request.GET:
                with safe_query_string(request):
                    newurl += '?' + request.META['QUERY_STRING']
            return HttpResponseRedirect(newurl)
        return response


class GroupAliasRedirectionMiddleware(object):
    """Redirect `group` requests to the alias `group` if it exists."""

    def process_response(self, request, response):
        group_url = re.match('^/group/(?P<url>[-\w]+)/$', request.path_info)
        if (response.status_code == 404
            and group_url
            and (GroupAlias.objects.filter(url=group_url.group('url'))
                 .exists())):

            group_alias = GroupAlias.objects.get(url=group_url.group('url'))
            newurl = reverse('group', args=[group_alias.alias.url])
            if request.GET:
                with safe_query_string(request):
                    newurl += '?' + request.META['QUERY_STRING']
            return HttpResponseRedirect(newurl)
        return response


@contextmanager
def safe_query_string(request):
    """Turn the QUERY_STRING into a unicode- and ascii-safe string.

    We need unicode so it can be combined with a reversed URL, but it
    has to be ascii to go in a Location header. iri_to_uri seems like
    a good compromise.
    """
    qs = request.META['QUERY_STRING']
    try:
        request.META['QUERY_STRING'] = iri_to_uri(qs)
        yield
    finally:
        request.META['QUERY_STRING'] = qs
