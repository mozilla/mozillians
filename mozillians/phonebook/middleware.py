import re

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.urlresolvers import is_valid_path, reverse
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext as _

from mozillians.common.templatetags.helpers import redirect
from mozillians.common.middleware import safe_query_string


class RegisterMiddleware(object):
    """Redirect authenticated users with incomplete profile to register view."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        path = request.path

        allow_urls = [
            r'^/[\w-]+{0}'.format(reverse('phonebook:logout')),
            r'^/[\w-]+{0}'.format(reverse('phonebook:login')),
            r'^/[\w-]+{0}'.format(reverse('phonebook:profile_edit')),
            r'^/[\w-]+{0}'.format(reverse('groups:skills-autocomplete')),
            r'^/[\w-]+{0}'.format(reverse('users:country-autocomplete')),
            r'^/[\w-]+{0}'.format(reverse('users:region-autocomplete')),
            r'^/[\w-]+{0}'.format(reverse('users:city-autocomplete')),
            r'^/[\w-]+{0}'.format(reverse('users:timezone-autocomplete')),
        ]

        if settings.DEBUG:
            allow_urls.append(settings.MEDIA_URL)

        if (user.is_authenticated() and not user.userprofile.is_complete and not
                filter(lambda url: re.match(url, path), allow_urls)):
            messages.warning(request, _('Please complete registration before proceeding.'))
            return redirect('phonebook:profile_edit')
        return self.get_response(request)


class UsernameRedirectionMiddleware(object):
    """
    Redirect requests for user profiles from /<username> to
    /u/<username> to avoid breaking profile urls with the new url
    schema.

    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if (response.status_code == 404 and not
            request.path_info.startswith('/u/')
            and not is_valid_path(request.path_info)
            and User.objects.filter(username__iexact=request.path_info[1:].strip('/')).exists()
            and request.user.is_authenticated()
                and request.user.userprofile.is_vouched):

            newurl = '/u' + request.path_info
            if request.GET:
                with safe_query_string(request):
                    newurl += '?' + request.META['QUERY_STRING']
            return HttpResponseRedirect(newurl)
        return response
