import logging

from django import http
from django.contrib.auth import forms as auth_forms, authenticate, login as auth_login
import django.contrib.auth.views
from django.shortcuts import redirect

import jingo

import larper
import larper.models

from . import forms

log = logging.getLogger('phonebook')


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

    return redirect(next)


def register(request):
    form = forms.RegistrationForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            uniq_id = _save_new_user(request, form)            
            return redirect('phonebook.edit_new_profile', uniq_id)
    return jingo.render(request, 'users/register.html',
                        dict(form=form))

def _save_new_user(request, form):
    """
    form - must be a valid form

    We persist account to LDAP. If all goes well, we 
    log the user in and persist their password to the session.
    """

    # Optional
    first_name = form.cleaned_data['first_name'].encode('utf-8') or ""
    
    email = form.cleaned_data['email'].encode('utf-8')
    password = form.cleaned_data['password'].encode('utf-8')
    last_name = form.cleaned_data['last_name'].encode('utf-8')
    
    display_name = ("%s %s" % (first_name, last_name)).encode('utf-8')
    # save to ldap
    profile = {
               'objectclass': ['inetOrgPerson','person','mozilliansPerson'],
               'cn': display_name,
               #'givenName': first_name,
               'sn': last_name,
               'displayName': display_name,
               'userPassword': password,
               'uid': email,
               'mail': email,
               }
    uniq_id = larper.create_person(request, profile, password)
    user = authenticate(username=email, password=password)
    log.debug("Logged user in %s" % user)
    if user:
        # update session
        auth_login(request, user)
        larper.store_password(request, password)
    return uniq_id
