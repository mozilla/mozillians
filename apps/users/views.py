import logging
log = logging.getLogger('phonebook')
log.addHandler(logging.StreamHandler())
log.setLevel(logging.DEBUG)

from django import http

from django.conf import settings

import django.contrib.auth.views

from django.contrib.auth import forms as auth_forms

def login(request):
    log.error("Logging out")
    logout(request)

    r = django.contrib.auth.views.login(request, template_name='users/login.html',
                         redirect_field_name='to',
                         authentication_form=auth_forms.AuthenticationForm)
    if isinstance(r, http.HttpResponseRedirect):
        # user id 1 password secret
        log.error('Success')
    else:
        log.error("FAILURE")
    return r

def logout(request):
    # Not using get_profile() becuase user could be anonymous
    user = request.user
    if not user.is_anonymous():
        log.error(u"User (%s) logged out" % user)

    django.contrib.auth.logout(request)

    next = request.GET.get('to') or '/'

    return http.HttpResponseRedirect(next)
