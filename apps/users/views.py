import ldap

from django import http
from django.contrib import auth, messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.http import (Http404, HttpResponse, HttpResponseRedirect,
                         HttpResponseForbidden)

import commonware.log
from funfactory.urlresolvers import reverse
from tower import ugettext as _

from phonebook.models import Invite
from session_csrf import anonymous_csrf
from users import forms
from users.models import UserProfile

log = commonware.log.getLogger('m.users')

get_invite = lambda c: Invite.objects.get(code=c, redeemed=None)


def logout(request, **kwargs):
    """Logout view that wraps Django's logout but always redirects.

    Django's contrib.auth.views logout method renders a template if the
    `next_page` argument is `None`, which we don't want. This view always
    returns an HTTP redirect instead.
    """
    return auth_views.logout(request, next_page=reverse('home'), **kwargs)


def password_reset_confirm(request, uidb36=None, token=None):
    """Legacy URL, keep around until 1.4 release."""
    return redirect('home')


@anonymous_csrf
def register(request):
    """Multi-purpose registration view.

    Uses: legacy email url with invite code, first time edit profile
    after browserid_login. Process POST and create new users.
    """
    # Legacy URL shenanigans - A GET to register with invite code
    # is a legal way to start the BrowserID registration flow.
    if 'code' in request.GET:
        request.session['invite-code'] = request.GET['code']
        return redirect('home')

    if request.user.is_authenticated():
        return redirect(reverse('profile', args=[request.user.unique_id]))

    assertion = request.session.get('assertion')
    audience = request.session.get('audience')
    if assertion == None or audience == None:
        log.error('Browserid registration, but no verified email in session')
        return redirect('home')

    user = auth.authenticate(assertion=assertion,
                             audience=audience)

    intent = 'register'

    # Check for optional invite code
    initial = {}
    if 'invite-code' in request.session:
        code = request.session['invite-code']
        try:
            invite = get_invite(code)
            initial['email'] = invite.recipient
            initial['code'] = invite.code
        except Invite.DoesNotExist:
            log.warning('Bad register code [%s], skipping invite' % code)

    form = forms.RegistrationForm(request.POST or None, initial=initial)

    if request.method == 'POST':
        if form.is_valid():
            auth.login(request, user)
            form.save(request)
            messages.info(request, _(u'Your account has been created.'))
            return redirect('profile', user.username)
    else:
        if 'link' in request.GET:
            intent = request.GET['link']

    return render(request, 'phonebook/edit_profile.html',
                  dict(form=form,
                       edit_form_action=reverse('register'),
                       person=user,
                       mode='new',
                       email=user.email,
                       intent=intent))


def _set_already_exists_error(form):
    msg = _('Someone has already registered an account with %(email)s.')
    data = dict(email=form.cleaned_data['email'])
    del form.cleaned_data['email']
    error = _(msg % data)
    form._errors['email'] = form.error_class([error])
