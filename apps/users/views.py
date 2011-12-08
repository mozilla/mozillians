import datetime
import ldap

from django.contrib import auth, messages
from django.contrib.auth import views as auth_views
from django.shortcuts import redirect, render

import commonware.log
from funfactory.urlresolvers import reverse
from statsd import statsd
from tower import ugettext as _

from larper import RegistrarSession, get_assertion
from phonebook.models import Invite
from session_csrf import anonymous_csrf
from users import forms
from users.models import Anonymous, UserProfile

log = commonware.log.getLogger('m.users')

get_invite = lambda c: Invite.objects.get(code=c, redeemed=None)


def logout(request, **kwargs):
    """Logout view that wraps Django's logout but always redirects.

    Django's contrib.auth.views logout method renders a template if the
    `next_page` argument is `None`, which we don't want. This view always
    returns an HTTP redirect instead.
    """
    return auth_views.logout(request, next_page=reverse('login'), **kwargs)


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

    if not 'verified_email' in request.session:
        log.error('Browserid registration, but no verified email in session')
        return redirect('home')

    email = request.session['verified_email']

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
            try:
                uniq_id = _save_new_user(request, form)
                messages.info(request, _(u'Your account has been created.'))
                return redirect('profile', uniq_id)
            except ldap.CONSTRAINT_VIOLATION:
                log.error("User already exists")
                _set_already_exists_error(form)
    else:
        if 'link' in request.GET:
            intent = request.GET['link']
    anonymous = Anonymous()

    return render(request, 'phonebook/edit_profile.html',
                  dict(form=form,
                       edit_form_action=reverse('register'),
                       person=anonymous,
                       mode='new',
                       email=email,
                       intent=intent))


def password_reset_confirm(request, uidb36=None, token=None):
    """Legacy URL, keep around until 1.4 release."""
    return redirect('home')


def _save_new_user(request, form):
    """
    form - must be a valid form

    We persist account to LDAP. If all goes well, we
    log the user in and persist their BID assertion to the
    session.
    """
    # Email in the form is the "username" we'll use.
    email = request.session['verified_email']
    username = email

    registrar = RegistrarSession.connect(request)

    code = request.session.get('invite-code')

    d = form.cleaned_data
    d['email'] = email
    uniq_id = registrar.create_person(d)
    voucher = None

    if code:
        try:
            invite = get_invite(code)
            voucher = invite.inviter
        except Invite.DoesNotExist:
            msg = 'Bad code in form [%s], skipping pre-vouch' % d['code']
            log.warning(msg)

    # we need to authenticate them... with their assertion
    assertion_hash, assertion = get_assertion(request)

    for i in range(1, 10):
        try:
            user = auth.authenticate(request=request, assertion=assertion)

            # Should never happen
            if not user or not user.is_authenticated():
                msg = 'Authentication for new user (%s) failed' % username
                # TODO: make this a unique exception.
                raise Exception(msg)

            statsd.incr('user.successful_registration')
            statsd.incr('user.successful_registration_attempt_%s' % i)
            break
        except Exception, e:
            statsd.incr('user.errors.registration_failed')
            statsd.incr('user.errors.registration_failed_attempt_%s' % i)
            log.warning(e)

            # All hope is lost.
            if i == 10:
                statsd.incr('user.errors.user_record_never_created')
                raise Exception(e)

    if voucher:
        # TODO: invite system should use FKs not UIDs.
        profile = user.get_profile()
        profile.vouch(UserProfile.objects.get_by_unique_id(uniq_id))
        invite.redeemed = datetime.datetime.now()
        invite.redeemer = uniq_id
        invite.save()

    # TODO: Remove when LDAP goes away
    auth.login(request, user)

    return uniq_id


def _set_already_exists_error(form):
    msg = _('Someone has already registered an account with %(email)s.')
    data = dict(email=form.cleaned_data['email'])
    del form.cleaned_data['email']
    error = _(msg % data)
    form._errors['email'] = form.error_class([error])
