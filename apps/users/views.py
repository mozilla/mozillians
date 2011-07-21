import logging

from django import http
from django.contrib.auth import forms as auth_forms
import django.contrib.auth.views

log = logging.getLogger('phonebook')

import larper

def login(request):
    logout(request)

    r = django.contrib.auth.views.login(
            request,
            template_name='users/login.html',
            redirect_field_name='to',
            authentication_form=auth_forms.AuthenticationForm)

    if isinstance(r, http.HttpResponseRedirect):
        log.debug("login success, storing password in session.")
        larper.store_password(request, request.POST['password'])
    else:
        log.debug("login failed")

    return r


def logout(request):
    # Not using get_profile() becuase user could be anonymous
    user = request.user
    if not user.is_anonymous():
        log.error(u"User (%s) logged out" % user)

    django.contrib.auth.logout(request)

    next = request.GET.get('to') or '/'

    return http.HttpResponseRedirect(next)


def register(request):
    pass
