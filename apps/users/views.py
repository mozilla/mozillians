import datetime
import ldap

from django.shortcuts import redirect
from django.contrib import auth

import commonware.log
import jingo
from tower import ugettext as _

from larper import RegistrarSession
from phonebook.models import Invite
from users import forms

log = commonware.log.getLogger('m.users')

get_invite = lambda c: Invite.objects.get(code=c, redeemed=None)


def register(request):
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
                uniq_id = _save_new_user(request, form)
                return redirect('phonebook.edit_new_profile', uniq_id)
            except ldap.CONSTRAINT_VIOLATION:
                _set_already_exists_error(form)
    return jingo.render(request, 'registration/register.html',
                        dict(form=form))


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

    if voucher:
        registrar.record_vouch(voucher=voucher, vouchee=uniq_id)
        invite.redeemed = datetime.datetime.now()
        invite.redeemer = uniq_id
        invite.save()

    user = auth.authenticate(username=username, password=password)
    auth.login(request, user)

    return uniq_id


def _set_already_exists_error(form):
    msg = _('Someone has already registered an account with %(email)s.')
    data = dict(email=form.cleaned_data['email'])
    del form.cleaned_data['email']
    error = _(msg % data)
    form._errors['username'] = form.error_class([error])
