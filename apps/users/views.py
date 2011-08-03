from django.shortcuts import redirect

from django.contrib import auth

import jingo

from larper import RegistrarSession

from . import forms


def register(request):
    form = forms.RegistrationForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            uniq_id = _save_new_user(request, form)
            return redirect('phonebook.edit_new_profile', uniq_id)
    return jingo.render(request, 'registration/register.html',
                        dict(form=form))


def _save_new_user(request, form):
    """
    form - must be a valid form

    We persist account to LDAP. If all goes well, we
    log the user in and persist their password to the session.
    """
    username = form.cleaned_data['username']
    password = form.cleaned_data['password']

    registrar = RegistrarSession.connect(request)
    uniq_id = registrar.create_person(form.cleaned_data)

    user = auth.authenticate(username=username, password=password)
    auth.login(request, user)

    return uniq_id
