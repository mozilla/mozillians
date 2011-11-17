import datetime
import ldap

from django import http
from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

import commonware.log
from funfactory.urlresolvers import reverse
from statsd import statsd
from tower import ugettext as _

from larper import RegistrarSession
from phonebook.models import Invite
from session_csrf import anonymous_csrf
from users import forms
from users.models import UserProfile

log = commonware.log.getLogger('m.users')

get_invite = lambda c: Invite.objects.get(code=c, redeemed=None)


def _send_confirmation_email(user):
    """This sends a confirmation email to the user."""
    subject = _('Confirm your account')
    message = (_("Please confirm your Mozillians account:\n\n %s") %
               user.get_profile().get_confirmation_url())
    send_mail(subject, message, 'no-reply@mozillians.org', [user.username])


def send_confirmation(request):
    user = request.GET['user']
    user = get_object_or_404(auth.models.User, username=user)
    _send_confirmation_email(user)
    return render(request, 'users/confirmation_sent.html')


def confirm(request):
    """Confirm a user's email address using a generated code.

    1. Recognize the code or 404.
    2. On recognition, mark user as confirmed.
    """
    code = request.GET.get('code')
    if not code:
        raise Http404

    profile = get_object_or_404(UserProfile, confirmation_code=code)
    profile.is_confirmed = True
    profile.save()
    return render(request, 'users/confirmed.html')


@anonymous_csrf
def login(request, **kwargs):
    """Login view that wraps Django's login but redirects auth'd users."""
    return (auth_views.login(request, **kwargs)
            if request.user.is_anonymous()
            else redirect(reverse('profile', args=[request.user.unique_id])))


def logout(request, **kwargs):
    """Logout view that wraps Django's logout but always redirects.

    Django's contrib.auth.views logout method renders a template if the
    `next_page` argument is `None`, which we don't want. This view always
    returns an HTTP redirect instead.
    """
    return auth_views.logout(request, next_page=reverse('login'), **kwargs)


@anonymous_csrf
def register(request):
    if request.user.is_authenticated():
        return redirect(reverse('profile', args=[request.user.unique_id]))

    initial = {}
    if 'code' in request.GET:
        code = request.GET['code']
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
                _save_new_user(request, form)
                _send_confirmation_email(request.user)

                msg = _(u'Your account has been created but needs to be '
                         'verified. Please check your email to verify '
                         'your account.')
                messages.info(request, msg)
                auth.logout(request)

                return redirect(reverse('login'))
            except ldap.CONSTRAINT_VIOLATION:
                _set_already_exists_error(form)
    return render(request, 'registration/register.html', dict(form=form))


def password_change(request):
    """
    View wraps django.auth.contrib's password_change view, so that
    we can override the form as well as logout the user.
    """
    r = auth.views.password_change(request,
                                   'registration/password_change_form.html',
                                   reverse('login'),
                                   forms.PasswordChangeForm)
    # Our session has the old password.
    if isinstance(r, http.HttpResponseRedirect):
        auth.logout(request)
    return r


def password_reset(request):
    """
    View wraps django.auth.contrib's password_reset view, so that
    we can override the form.
    """
    r = auth.views.password_reset(request,
                                  False,
                                  'registration/password_reset_form.html',
                                  'registration/password_reset_email.html',
                                  'registration/password_reset_subject.txt',
                                  forms.PasswordResetForm,
                                  default_token_generator,
                                  reverse('password_reset_check_mail'))
    return r


def password_reset_confirm(request, uidb36=None, token=None):
    """
    View wraps django.auth.contrib's password_reset_confirm view, so that
    we can override the form.
    """
    r = auth.views.password_reset_confirm(
        request,
        uidb36,
        token,
        'registration/password_reset_confirm.html',
        default_token_generator,
        forms.SetPasswordForm,
        reverse('login'))
    return r


def password_reset_check_mail(request):
    return render(request, 'registration/password_reset_check_mail.html')


def _save_new_user(request, form):
    """
    form - must be a valid form

    We persist account to LDAP. If all goes well, we
    log the user in and persist their password to the session.
    """
    # Email in the form is the "username" we'll use.
    username = form.cleaned_data['email']
    password = form.cleaned_data['password']
    registrar = RegistrarSession.connect(request)

    d = form.cleaned_data
    uniq_id = registrar.create_person(d)

    voucher = None

    if d['code']:
        try:
            invite = get_invite(d['code'])
            voucher = invite.inviter
        except Invite.DoesNotExist:
            msg = 'Bad code in form [%s], skipping pre-vouch' % d['code']
            log.warning(msg)

    for i in range(1, 10):
        try:
            user = auth.authenticate(username=username, password=password)

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

    # TODO: Remove when LDAP goes away
    auth.login(request, user)

    profile = user.get_profile()

    if voucher:
        # TODO: invite system should use FKs not UIDs.
        profile.vouch(UserProfile.objects.get_by_unique_id(uniq_id))
        invite.redeemed = datetime.datetime.now()
        invite.redeemer = uniq_id
        invite.save()

    return uniq_id


def _set_already_exists_error(form):
    msg = _('Someone has already registered an account with %(email)s.')
    data = dict(email=form.cleaned_data['email'])
    del form.cleaned_data['email']
    error = _(msg % data)
    form._errors['email'] = form.error_class([error])
