from django.http import HttpResponse
from django.http import Http404
from django.shortcuts import redirect
from django.views.decorators.http import require_POST

import django.contrib.auth

from commons.urlresolvers import reverse

import jingo
from tower import ugettext as _

from larper import UserSession, AdminSession, NO_SUCH_PERSON

from . import forms


def profile_uid(request, unique_id):
    """
    unique_id is a stable, random user id.
    """
    ldap = UserSession.connect(request)
    try:
        person = ldap.get_by_unique_id(unique_id)
        if person.last_name:
            return _profile(request, person)
    except NO_SUCH_PERSON:
        raise Http404


def profile_nickname(request, nickname):
    """
    This is probably post 1.0, but we could provide
    a nicer url if we used let the user opt-in to
    a Mozillians nickname (pre-populated from their
    IRC nickname)
    """
    person = do_some_magic(nickname)
    return _profile(request, person)


def _profile(request, person):
    vouch_form = None
    ldap = UserSession.connect(request)

    if person.voucher_unique_id:
        person.voucher = ldap.get_by_unique_id(person.voucher_unique_id)
    elif request.user.unique_id != person.unique_id:
        voucher = request.user.unique_id
        vouch_form = forms.VouchForm(initial=dict(
                voucher=voucher,
                vouchee=person.unique_id))

    return jingo.render(request, 'phonebook/profile.html',
                        dict(person=person, vouch_form=vouch_form))


def edit_profile(request, unique_id):
    """ Why does this and edit_new_profile accept a unique_id
    Instead of just using the request.user object?

    LDAP's ACL owns if the current user can edit the user or not.
    We get a rich admin screen for free, for LDAPAdmin users.
    """
    return _edit_profile(request, unique_id, False)


def edit_new_profile(request, unique_id):
    return _edit_profile(request, unique_id, True)


def _edit_profile(request, unique_id, new_account):
    ldap = UserSession.connect(request)
    person = ldap.get_by_unique_id(unique_id)

    del_form = forms.DeleteForm(
        initial={'unique_id': unique_id})
    if person:
        if request.method == 'POST':
            form = forms.ProfileForm(request.POST, request.FILES)
            if form.is_valid():
                ldap = UserSession.connect(request)
                ldap.update_person(unique_id, form.cleaned_data)
                ldap.update_profile_photo(unique_id, form.cleaned_data)
                if new_account:
                    return redirect('confirm_register')
                else:
                    return redirect('profile', unique_id)
        else:
            form = forms.ProfileForm(initial={
                    'first_name': person.first_name,
                    'last_name': person.last_name,
                    'biography': person.biography, })

        return jingo.render(request, 'phonebook/edit_profile.html', dict(
                form=form,
                delete_form=del_form,
                person=person,
                registration_flow=new_account,
                ))
    else:
        raise Http404


class UNAUTHORIZED_DELETE(Exception):
    pass


@require_POST
def delete(request):
    form = forms.DeleteForm(request.POST)
    if form.is_valid() and _user_owns_account(request, form):
        admin_ldap = AdminSession.connect(request)
        admin_ldap.delete_person(form.cleaned_data['unique_id'])
        django.contrib.auth.logout(request)
    else:
        raise UNAUTHORIZED_DELETE("Unauthorized deletion of account, attempted")

    return redirect('home')


def _user_owns_account(request, form):
    """
    A leak in our authentication abstraction...
    We use a shared Admin account for deleting, so
    we can't rely on LDAP ACL to test this for us.
    We must ensure the current user is the same as the
    account to be deleted.
    """
    uniq_id_to_delete = form.cleaned_data['unique_id']
    return request.user.unique_id == uniq_id_to_delete


def search(request):
    people = []
    form = forms.SearchForm(request.GET)
    if form.is_valid():
        query = form.cleaned_data.get('q', '')
        if request.user.is_authenticated():
            ldap = UserSession.connect(request)
            people = ldap.search(query)

    return jingo.render(request, 'phonebook/search.html',
                        dict(people=people))


def photo(request, unique_id):
    ldap = UserSession.connect(request)
    image = ldap.profile_photo(unique_id)
    if image:
        return HttpResponse(image, mimetype="image/jpeg")
    else:
        return redirect('/media/img/unknown.png')


def invite(request):
    # TODO(davedash): actually send this
    subject = _('Become a Mozillian')
    message = _("Hi, I'm sending you this because I think you should join "
                'mozillians.org, the community directory for Mozilla '
                'contributors like you. You can create a profile for yourself '
                'about what you do in the community as well as search for '
                'other contributors to learn more about them or get in touch. '
                'Check it out.')

    return jingo.render(request, 'phonebook/invite.html')


@require_POST
def vouch(request):
    form = forms.VouchForm(request.POST)
    if form.is_valid():
        ldap = UserSession.connect(request)
        data = form.cleaned_data
        vouchee = data.get('vouchee')
        ldap.record_vouch(data.get('voucher'), vouchee)
        return redirect(reverse('profile', args=[vouchee]))
