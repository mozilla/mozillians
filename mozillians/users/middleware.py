import re

from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect

from tower import ugettext as _


class RegisterMiddleware():
    """Redirect authenticated users with incomplete profile to register view."""
    def process_request(self, request):
        user = request.user
        path = request.path
        allow_urls = [r'^/[\w-]+{0}'.format(reverse('logout')),
                      r'^/[\w-]+{0}'.format(reverse('login')),
                      r'^/[\w-]+{0}'.format(reverse('profile.edit')),
                      r'^/browserid/',
                      r'^/[\w-]+/jsi18n/']

        if settings.DEBUG:
            allow_urls.append(settings.MEDIA_URL)

        if (user.is_authenticated() and not user.userprofile.is_complete
            and not filter(lambda url: re.match(url, path), allow_urls)):
            messages.warning(request, _('Please complete registration '
                                        'before proceeding.'))
            return redirect('profile.edit')
